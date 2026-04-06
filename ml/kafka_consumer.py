"""
ML-side Kafka consumer. Reads from metrics-stream, maintains a rolling 60-point
buffer per service, and calls the inference server once the buffer is full.

The rolling buffer approach means we always have the most recent 15 minutes of
history. We don't wait for a fixed window to complete — every new reading shifts
the window forward and triggers a new prediction. This gives us continuous scoring
rather than batch scoring every 15 minutes.

One thing to watch: if a service goes quiet (RPS drops to zero), the buffer stops
updating and the last prediction stays stale. The inference server's Prometheus
gauge will hold the last value. That's usually fine — if the service is dead,
the Prometheus scrape will fail and you'll get a ServiceDown alert anyway.
"""
import os
import json
import time
import logging
import requests
from collections import defaultdict, deque
from kafka import KafkaConsumer, KafkaProducer

log = logging.getLogger("ml-consumer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
METRICS_TOPIC   = os.getenv("KAFKA_METRICS_TOPIC",     "metrics-stream")
ALERTS_TOPIC    = os.getenv("KAFKA_ALERTS_TOPIC",      "anomaly-alerts")
INFERENCE_URL   = os.getenv("INFERENCE_SERVER_URL",    "http://localhost:8080")
SEQ_LEN         = int(os.getenv("SEQ_LEN", "60"))
KAFKA_SASL_USERNAME = os.getenv("KAFKA_SASL_USERNAME", "")
KAFKA_SASL_PASSWORD = os.getenv("KAFKA_SASL_PASSWORD", "")

# one rolling buffer per service
buffers: dict[str, deque] = defaultdict(lambda: deque(maxlen=SEQ_LEN))

FEATURE_ORDER = [
    "cpu_usage_percent",
    "memory_usage_percent",
    "request_latency_p99",
    "error_rate_percent",
    "requests_per_second",
]


def extract_features(metrics: dict) -> list[float]:
    return [metrics.get(k, 0.0) for k in FEATURE_ORDER]


def _kafka_kwargs(extra: dict) -> dict:
    """Build Kafka connection kwargs, adding SASL if credentials are set."""
    kwargs = {"bootstrap_servers": KAFKA_BOOTSTRAP, **extra}
    if KAFKA_SASL_USERNAME and KAFKA_SASL_PASSWORD:
        kwargs.update({
            "security_protocol":   "SASL_SSL",
            "sasl_mechanism":      "PLAIN",
            "sasl_plain_username": KAFKA_SASL_USERNAME,
            "sasl_plain_password": KAFKA_SASL_PASSWORD,
        })
    return kwargs


def run():
    consumer = KafkaConsumer(
        METRICS_TOPIC,
        **_kafka_kwargs({
            "auto_offset_reset":  "latest",
            "value_deserializer": lambda m: json.loads(m.decode()),
            "group_id":           "ml-inference-consumer",
        })
    )
    producer = KafkaProducer(
        **_kafka_kwargs({"value_serializer": lambda v: json.dumps(v).encode()})
    )

    log.info(f"consuming {METRICS_TOPIC} → inference → {ALERTS_TOPIC}")

    for msg in consumer:
        data      = msg.value
        service   = data.get("service")
        metrics   = data.get("metrics", {})
        timestamp = data.get("timestamp", time.time())

        buffers[service].append(extract_features(metrics))

        if len(buffers[service]) < SEQ_LEN:
            continue  # still warming up

        try:
            resp = requests.post(
                f"{INFERENCE_URL}/predict",
                json={"service": service, "sequence": list(buffers[service])},
                timeout=5,
            )
            resp.raise_for_status()
            result = resp.json()
        except Exception as e:
            log.warning(f"inference failed for {service}: {e}")
            continue

        score      = result.get("anomaly_score", 0.0)
        is_anomaly = result.get("is_anomaly", False)

        if is_anomaly:
            alert = {
                "service":          service,
                "anomaly_score":    score,
                "threshold":        result.get("threshold"),
                "timestamp":        timestamp,
                "top_features":     result.get("top_features", {}),
                "metrics_snapshot": metrics,
            }
            producer.send(ALERTS_TOPIC, value=alert)
            producer.flush()
            log.warning(f"anomaly | {service} | score={score:.4f} | top={result.get('top_features', {})}")


if __name__ == "__main__":
    run()
