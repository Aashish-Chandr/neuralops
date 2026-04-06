"""
Kafka Consumer for the ML layer.
Reads from metrics-stream, batches into sequences of 60, calls inference server,
publishes anomaly alerts to anomaly-alerts topic.
"""
import os
import json
import time
import logging
import requests
from collections import defaultdict, deque
from kafka import KafkaConsumer, KafkaProducer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("ml-kafka-consumer")

KAFKA_BOOTSTRAP    = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
METRICS_TOPIC      = os.getenv("KAFKA_METRICS_TOPIC",     "metrics-stream")
ALERTS_TOPIC       = os.getenv("KAFKA_ALERTS_TOPIC",      "anomaly-alerts")
INFERENCE_URL      = os.getenv("INFERENCE_SERVER_URL",    "http://localhost:8080")
SEQ_LEN            = int(os.getenv("SEQ_LEN", "60"))
CONSUMER_GROUP     = "ml-inference-consumer"

# Rolling buffer per service: stores last SEQ_LEN metric readings
buffers: dict[str, deque] = defaultdict(lambda: deque(maxlen=SEQ_LEN))

FEATURE_KEYS = ["cpu_usage_percent", "memory_usage_percent", "request_latency_p99",
                "error_rate_percent", "requests_per_second"]


def make_producer() -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )


def make_consumer() -> KafkaConsumer:
    return KafkaConsumer(
        METRICS_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        auto_offset_reset="latest",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        group_id=CONSUMER_GROUP,
    )


def extract_features(metrics: dict) -> list[float]:
    return [
        metrics.get("cpu_usage_percent", 0.0),
        metrics.get("memory_usage_percent", 0.0),
        metrics.get("request_latency_p99", 0.0),
        metrics.get("error_rate_percent", 0.0),
        metrics.get("requests_per_second", 0.0),
    ]


def run():
    consumer = make_consumer()
    producer = make_producer()
    log.info(f"Consuming from '{METRICS_TOPIC}', publishing alerts to '{ALERTS_TOPIC}'")

    for msg in consumer:
        data = msg.value
        service = data.get("service")
        metrics = data.get("metrics", {})
        timestamp = data.get("timestamp", time.time())

        features = extract_features(metrics)
        buffers[service].append(features)

        if len(buffers[service]) < SEQ_LEN:
            continue  # not enough history yet

        sequence = list(buffers[service])  # (60, 5)

        try:
            resp = requests.post(
                f"{INFERENCE_URL}/predict",
                json={"service": service, "sequence": sequence},
                timeout=5,
            )
            result = resp.json()
        except Exception as e:
            log.warning(f"Inference call failed for {service}: {e}")
            continue

        score = result.get("anomaly_score", 0.0)
        is_anomaly = result.get("is_anomaly", False)
        log.debug(f"{service} score={score:.4f} anomaly={is_anomaly}")

        if is_anomaly:
            alert = {
                "service": service,
                "anomaly_score": score,
                "threshold": result.get("threshold"),
                "timestamp": timestamp,
                "top_features": result.get("top_features", {}),
                "metrics_snapshot": metrics,
            }
            producer.send(ALERTS_TOPIC, value=alert)
            producer.flush()
            log.warning(f"ANOMALY ALERT: {service} score={score:.4f} | {alert['top_features']}")


if __name__ == "__main__":
    run()
