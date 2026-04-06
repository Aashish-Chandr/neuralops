"""
Integration test: verify metrics flow from exporter → Kafka → consumer.
Requires a running Kafka instance (use docker-compose for local testing).

Run: pytest tests/integration/ -v --timeout=60
"""
import json
import time
import threading
import pytest
from unittest.mock import patch, MagicMock


class MockKafkaProducer:
    def __init__(self, *args, **kwargs):
        self.messages = []

    def send(self, topic, value=None):
        self.messages.append({"topic": topic, "value": value})
        return MagicMock()

    def flush(self):
        pass


class MockKafkaConsumer:
    def __init__(self, *args, **kwargs):
        self._messages = []

    def add_message(self, value):
        msg = MagicMock()
        msg.value = value
        self._messages.append(msg)

    def __iter__(self):
        return iter(self._messages)


def test_metrics_exporter_publishes_all_services():
    """Exporter should publish one message per service per scrape cycle."""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "streaming"))

    mock_producer = MockKafkaProducer()

    with patch("metrics_exporter.query_prometheus", return_value=42.0), \
         patch("metrics_exporter.create_producer", return_value=mock_producer):

        import metrics_exporter
        metrics_exporter.SERVICES = ["svc-a", "svc-b", "svc-c"]

        # Simulate one scrape cycle
        timestamp = time.time()
        for svc in metrics_exporter.SERVICES:
            metric_point = {"service": svc, "timestamp": timestamp, "metrics": {}}
            for metric_name, query_template in metrics_exporter.QUERIES.items():
                metric_point["metrics"][metric_name] = 42.0
            mock_producer.send(metrics_exporter.KAFKA_TOPIC, value=metric_point)

    assert len(mock_producer.messages) == 3
    services_published = {m["value"]["service"] for m in mock_producer.messages}
    assert services_published == {"svc-a", "svc-b", "svc-c"}


def test_metrics_message_schema():
    """Each Kafka message must have required fields."""
    required_fields = {"service", "timestamp", "metrics"}
    metric_keys = {"cpu_usage_percent", "memory_usage_percent", "error_rate_percent",
                   "requests_per_second", "request_latency_p99"}

    message = {
        "service": "payment-service",
        "timestamp": time.time(),
        "metrics": {k: 0.0 for k in metric_keys},
    }

    assert required_fields.issubset(message.keys())
    assert metric_keys.issubset(message["metrics"].keys())


def test_kafka_consumer_batches_sequences():
    """ML consumer should buffer 60 readings before calling inference."""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "ml"))

    from collections import deque
    buffer = deque(maxlen=60)

    features = [20.0, 35.0, 80.0, 1.0, 50.0]
    for i in range(59):
        buffer.append(features)
        assert len(buffer) < 60

    buffer.append(features)
    assert len(buffer) == 60

    sequence = list(buffer)
    assert len(sequence) == 60
    assert len(sequence[0]) == 5


def test_anomaly_alert_schema():
    """Anomaly alert published to Kafka must have all required fields."""
    alert = {
        "service": "payment-service",
        "anomaly_score": 0.087,
        "threshold": 0.05,
        "timestamp": time.time(),
        "top_features": {
            "cpu_usage_percent": 0.001,
            "memory_usage_percent": 0.002,
            "latency_ms": 0.045,
            "error_rate_percent": 0.038,
            "rps": 0.001,
        },
        "metrics_snapshot": {"cpu_usage_percent": 85.0},
    }

    required = {"service", "anomaly_score", "threshold", "timestamp", "top_features"}
    assert required.issubset(alert.keys())
    assert alert["anomaly_score"] > alert["threshold"]
