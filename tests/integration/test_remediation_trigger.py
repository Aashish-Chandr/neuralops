"""
Integration test: alert → remediation engine → correct K8s action.
Mocks the Kubernetes client to verify the right API calls are made.
"""
import sys, os
import pytest
from unittest.mock import MagicMock, patch, call

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "remediation"))


def make_alert(cpu=20, mem=30, err=1, rps=50, lat=80, score=0.08):
    return {
        "service": "payment-service",
        "anomaly_score": score,
        "threshold": 0.05,
        "timestamp": 1234567890.0,
        "top_features": {},
        "metrics_snapshot": {
            "cpu_usage_percent": cpu,
            "memory_usage_percent": mem,
            "error_rate_percent": err,
            "requests_per_second": rps,
            "request_latency_p99": lat,
        },
    }


def test_crash_pattern_triggers_restart():
    from engine import classify_anomaly, restart_pod
    alert = make_alert(cpu=10, mem=20, err=45, rps=1, lat=50)
    assert classify_anomaly(alert) == "restart"


def test_overload_pattern_triggers_scale_up():
    from engine import classify_anomaly
    alert = make_alert(cpu=90, mem=85, err=5, rps=200, lat=800)
    assert classify_anomaly(alert) == "scale_up"


def test_bad_deploy_triggers_rollback():
    from engine import classify_anomaly
    alert = make_alert(cpu=30, mem=40, err=35, rps=50, lat=100)
    assert classify_anomaly(alert) == "rollback"


def test_restart_pod_calls_k8s_delete():
    """restart_pod should call delete_namespaced_pod."""
    from engine import restart_pod
    import engine

    mock_core = MagicMock()
    mock_pod = MagicMock()
    mock_pod.metadata.name = "payment-service-abc123"
    mock_core.list_namespaced_pod.return_value.items = [mock_pod]

    original = engine.core_api
    engine.core_api = mock_core
    try:
        result = restart_pod("payment-service")
        assert result is True
        mock_core.delete_namespaced_pod.assert_called_once_with(
            name="payment-service-abc123",
            namespace=engine.K8S_NAMESPACE,
        )
    finally:
        engine.core_api = original


def test_scale_up_calls_k8s_patch():
    """scale_up should call patch_namespaced_deployment_scale."""
    from engine import scale_up
    import engine

    mock_apps = MagicMock()
    original = engine.apps_api
    engine.apps_api = mock_apps
    try:
        result = scale_up("payment-service")
        assert result is True
        mock_apps.patch_namespaced_deployment_scale.assert_called_once()
        call_kwargs = mock_apps.patch_namespaced_deployment_scale.call_args
        assert call_kwargs[1]["name"] == "payment-service"
    finally:
        engine.apps_api = original


def test_audit_log_written(tmp_path):
    """Every action should write to the audit log."""
    from engine import audit
    import engine

    log_path = str(tmp_path / "audit.jsonl")
    original = engine.AUDIT_LOG_PATH
    engine.AUDIT_LOG_PATH = log_path

    try:
        audit("restart", "payment-service", "high errors", "success",
              {"anomaly_score": 0.08, "top_features": {}})

        with open(log_path) as f:
            entry = __import__("json").loads(f.read().strip())

        assert entry["action"] == "restart"
        assert entry["service"] == "payment-service"
        assert entry["result"] == "success"
        assert "timestamp" in entry
    finally:
        engine.AUDIT_LOG_PATH = original
