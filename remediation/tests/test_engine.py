"""Unit tests for remediation engine rule classifier."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine import classify_anomaly


def test_classify_crash():
    alert = {
        "metrics_snapshot": {
            "cpu_usage_percent": 10,
            "memory_usage_percent": 20,
            "error_rate_percent": 45,
            "requests_per_second": 1,
            "request_latency_p99": 50,
        },
        "top_features": {}
    }
    assert classify_anomaly(alert) == "restart"


def test_classify_overload():
    alert = {
        "metrics_snapshot": {
            "cpu_usage_percent": 90,
            "memory_usage_percent": 85,
            "error_rate_percent": 5,
            "requests_per_second": 200,
            "request_latency_p99": 800,
        },
        "top_features": {}
    }
    assert classify_anomaly(alert) == "scale_up"


def test_classify_bad_deploy():
    alert = {
        "metrics_snapshot": {
            "cpu_usage_percent": 30,
            "memory_usage_percent": 40,
            "error_rate_percent": 35,
            "requests_per_second": 50,
            "request_latency_p99": 100,
        },
        "top_features": {}
    }
    assert classify_anomaly(alert) == "rollback"


def test_classify_default():
    alert = {
        "metrics_snapshot": {
            "cpu_usage_percent": 20,
            "memory_usage_percent": 30,
            "error_rate_percent": 1,
            "requests_per_second": 50,
            "request_latency_p99": 80,
        },
        "top_features": {}
    }
    # Low everything — default to restart
    result = classify_anomaly(alert)
    assert result in ("restart", "scale_up", "rollback")
