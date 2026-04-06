"""
Metrics Exporter — reads from Prometheus HTTP API and publishes to Kafka.
Runs continuously, polling every SCRAPE_INTERVAL seconds.
"""
import os
import json
import time
import logging
import requests
from kafka import KafkaProducer
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("metrics-exporter")

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_METRICS_TOPIC", "metrics-stream")
SCRAPE_INTERVAL = int(os.getenv("SCRAPE_INTERVAL_SECONDS", "15"))

SERVICES = ["user-service", "order-service", "payment-service", "inventory-service", "notification-service"]

QUERIES = {
    "cpu_usage_percent":    'cpu_usage_percent{{service="{svc}"}}',
    "memory_usage_percent": 'memory_usage_percent{{service="{svc}"}}',
    "error_rate_percent":   'error_rate_percent{{service="{svc}"}}',
    "requests_per_second":  'requests_per_second{{service="{svc}"}}',
    "request_latency_p99":  'histogram_quantile(0.99, rate(http_request_duration_seconds_bucket{{service="{svc}"}}[1m]))',
}


def query_prometheus(query: str) -> float | None:
    try:
        resp = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": query},
            timeout=5,
        )
        data = resp.json()
        results = data.get("data", {}).get("result", [])
        if results:
            return float(results[0]["value"][1])
    except Exception as e:
        log.warning(f"Prometheus query failed: {e}")
    return None


def create_producer() -> KafkaProducer:
    while True:
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                retries=5,
            )
            log.info(f"Connected to Kafka at {KAFKA_BOOTSTRAP}")
            return producer
        except Exception as e:
            log.error(f"Kafka connection failed: {e}. Retrying in 5s...")
            time.sleep(5)


def main():
    producer = create_producer()
    log.info(f"Exporting metrics to topic '{KAFKA_TOPIC}' every {SCRAPE_INTERVAL}s")

    while True:
        timestamp = time.time()
        for svc in SERVICES:
            metric_point = {"service": svc, "timestamp": timestamp, "metrics": {}}
            for metric_name, query_template in QUERIES.items():
                query = query_template.format(svc=svc)
                value = query_prometheus(query)
                metric_point["metrics"][metric_name] = value if value is not None else 0.0

            producer.send(KAFKA_TOPIC, value=metric_point)
            log.debug(f"Published metrics for {svc}: {metric_point['metrics']}")

        producer.flush()
        log.info(f"Published metrics for {len(SERVICES)} services")
        time.sleep(SCRAPE_INTERVAL)


if __name__ == "__main__":
    main()
