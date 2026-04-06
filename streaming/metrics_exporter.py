"""
Prometheus → Kafka bridge.

Polls Prometheus every SCRAPE_INTERVAL seconds and publishes one JSON message
per service per cycle to the metrics-stream topic.

Why not just consume Prometheus directly from the ML side? Because Prometheus
is a pull-based system — it scrapes on its own schedule and stores data in its
TSDB. The ML consumer needs a push-based stream it can buffer from. Kafka gives
us that, plus replay capability if the inference server goes down temporarily.

The retry loop in create_producer() is intentional. On first startup, Kafka
might not be ready yet even with the healthcheck — there's a brief window where
the broker is up but not accepting connections. Retrying with backoff handles it.
"""
import os
import json
import time
import logging
import requests
from kafka import KafkaProducer
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger("metrics-exporter")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

PROMETHEUS_URL  = os.getenv("PROMETHEUS_URL",           "http://localhost:9090")
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS",  "localhost:9092")
KAFKA_TOPIC     = os.getenv("KAFKA_METRICS_TOPIC",      "metrics-stream")
SCRAPE_INTERVAL = int(os.getenv("SCRAPE_INTERVAL_SECONDS", "15"))

# Confluent Cloud (and most managed Kafka) requires SASL auth.
# Set these env vars when using Confluent Cloud free tier:
#   KAFKA_SASL_USERNAME  = your Confluent API key
#   KAFKA_SASL_PASSWORD  = your Confluent API secret
KAFKA_SASL_USERNAME = os.getenv("KAFKA_SASL_USERNAME", "")
KAFKA_SASL_PASSWORD = os.getenv("KAFKA_SASL_PASSWORD", "")

SERVICES = [
    "user-service",
    "order-service",
    "payment-service",
    "inventory-service",
    "notification-service",
]

# PromQL queries per metric. Double braces escape the format string.
QUERIES = {
    "cpu_usage_percent":    'cpu_usage_percent{{service="{svc}"}}',
    "memory_usage_percent": 'memory_usage_percent{{service="{svc}"}}',
    "error_rate_percent":   'error_rate_percent{{service="{svc}"}}',
    "requests_per_second":  'requests_per_second{{service="{svc}"}}',
    "request_latency_p99":  'histogram_quantile(0.99, rate(http_request_duration_seconds_bucket{{service="{svc}"}}[1m]))',
}


def query_prometheus(q: str) -> float | None:
    try:
        resp = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": q},
            timeout=5,
        )
        results = resp.json().get("data", {}).get("result", [])
        return float(results[0]["value"][1]) if results else None
    except Exception as e:
        log.warning(f"prometheus query failed: {e}")
        return None


def create_producer() -> KafkaProducer:
    backoff = 2
    # build kwargs — add SASL if credentials are provided (Confluent Cloud)
    kwargs: dict = {
        "bootstrap_servers": KAFKA_BOOTSTRAP,
        "value_serializer":  lambda v: json.dumps(v).encode(),
        "retries":           5,
        "acks":              "all",
    }
    if KAFKA_SASL_USERNAME and KAFKA_SASL_PASSWORD:
        kwargs.update({
            "security_protocol":  "SASL_SSL",
            "sasl_mechanism":     "PLAIN",
            "sasl_plain_username": KAFKA_SASL_USERNAME,
            "sasl_plain_password": KAFKA_SASL_PASSWORD,
        })

    while True:
        try:
            p = KafkaProducer(**kwargs)
            log.info(f"connected to kafka at {KAFKA_BOOTSTRAP}")
            return p
        except Exception as e:
            log.error(f"kafka connection failed: {e} — retrying in {backoff}s")
            time.sleep(backoff)
            backoff = min(backoff * 2, 30)


def main():
    producer = create_producer()
    log.info(f"publishing to '{KAFKA_TOPIC}' every {SCRAPE_INTERVAL}s")

    while True:
        ts = time.time()
        for svc in SERVICES:
            point = {"service": svc, "timestamp": ts, "metrics": {}}
            for name, tmpl in QUERIES.items():
                val = query_prometheus(tmpl.format(svc=svc))
                point["metrics"][name] = val if val is not None else 0.0
            producer.send(KAFKA_TOPIC, value=point)

        producer.flush()
        log.info(f"published {len(SERVICES)} services")
        time.sleep(SCRAPE_INTERVAL)


if __name__ == "__main__":
    main()
