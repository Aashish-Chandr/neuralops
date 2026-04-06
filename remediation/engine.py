"""
NeuralOps Auto-Remediation Engine
Consumes anomaly alerts from Kafka and takes automated action on Kubernetes.
"""
import os
import json
import time
import logging
import requests
from datetime import datetime, timezone
from kafka import KafkaConsumer, KafkaProducer
from kubernetes import client, config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
log = logging.getLogger("remediation-engine")

KAFKA_BOOTSTRAP    = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
ALERTS_TOPIC       = os.getenv("KAFKA_ALERTS_TOPIC",      "anomaly-alerts")
INFERENCE_URL      = os.getenv("INFERENCE_SERVER_URL",    "http://inference-server:8080")
K8S_NAMESPACE      = os.getenv("K8S_NAMESPACE",           "neuralops")
SLACK_WEBHOOK      = os.getenv("SLACK_WEBHOOK_URL",       "")
VERIFY_WAIT_SEC    = int(os.getenv("VERIFY_WAIT_SECONDS", "300"))  # 5 min
SCALE_UP_REPLICAS  = int(os.getenv("SCALE_UP_REPLICAS",   "3"))

# Audit log file
AUDIT_LOG_PATH = os.getenv("AUDIT_LOG_PATH", "/var/log/neuralops/remediation_audit.jsonl")


def load_k8s():
    try:
        config.load_incluster_config()
        log.info("Loaded in-cluster Kubernetes config")
    except Exception:
        try:
            config.load_kube_config()
            log.info("Loaded local kubeconfig")
        except Exception as e:
            log.warning(f"Could not load k8s config: {e}. K8s actions will be simulated.")
            return None, None
    return client.CoreV1Api(), client.AppsV1Api()


core_api, apps_api = load_k8s()


def audit(action: str, service: str, reason: str, result: str, alert: dict):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "service": service,
        "reason": reason,
        "result": result,
        "anomaly_score": alert.get("anomaly_score"),
        "top_features": alert.get("top_features", {}),
    }
    log.info(f"AUDIT | {action} | {service} | {result} | score={alert.get('anomaly_score', 0):.4f}")
    try:
        os.makedirs(os.path.dirname(AUDIT_LOG_PATH), exist_ok=True)
        with open(AUDIT_LOG_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        log.warning(f"Could not write audit log: {e}")


def escalate(service: str, alert: dict, message: str):
    log.error(f"ESCALATION: {service} — {message}")
    if SLACK_WEBHOOK:
        try:
            requests.post(SLACK_WEBHOOK, json={
                "text": f":rotating_light: *NeuralOps Escalation*\nService: `{service}`\n{message}\nScore: {alert.get('anomaly_score', 0):.4f}"
            }, timeout=5)
        except Exception as e:
            log.warning(f"Slack webhook failed: {e}")


def restart_pod(service: str) -> bool:
    """Delete the failing pod — Kubernetes will restart it automatically."""
    if core_api is None:
        log.info(f"[SIMULATED] Restarting pod for {service}")
        return True
    try:
        pods = core_api.list_namespaced_pod(
            namespace=K8S_NAMESPACE,
            label_selector=f"app={service}",
        )
        if not pods.items:
            log.warning(f"No pods found for {service}")
            return False
        pod_name = pods.items[0].metadata.name
        core_api.delete_namespaced_pod(name=pod_name, namespace=K8S_NAMESPACE)
        log.info(f"Deleted pod {pod_name} for {service} — k8s will restart it")
        return True
    except Exception as e:
        log.error(f"Failed to restart pod for {service}: {e}")
        return False


def scale_up(service: str) -> bool:
    """Scale the deployment up to handle overload."""
    if apps_api is None:
        log.info(f"[SIMULATED] Scaling up {service} to {SCALE_UP_REPLICAS} replicas")
        return True
    try:
        apps_api.patch_namespaced_deployment_scale(
            name=service,
            namespace=K8S_NAMESPACE,
            body={"spec": {"replicas": SCALE_UP_REPLICAS}},
        )
        log.info(f"Scaled {service} to {SCALE_UP_REPLICAS} replicas")
        return True
    except Exception as e:
        log.error(f"Failed to scale {service}: {e}")
        return False


def rollback(service: str) -> bool:
    """Rollback deployment to previous revision."""
    if apps_api is None:
        log.info(f"[SIMULATED] Rolling back {service}")
        return True
    try:
        # Patch with rollback annotation
        apps_api.patch_namespaced_deployment(
            name=service,
            namespace=K8S_NAMESPACE,
            body={"spec": {"rollbackTo": {"revision": 0}}},
        )
        log.info(f"Rollback triggered for {service}")
        return True
    except Exception as e:
        log.error(f"Failed to rollback {service}: {e}")
        return False


def classify_anomaly(alert: dict) -> str:
    """
    Rule-based classifier: determines remediation action from metric patterns.
    Returns: 'restart' | 'scale_up' | 'rollback'
    """
    features = alert.get("top_features", {})
    metrics  = alert.get("metrics_snapshot", {})

    cpu    = metrics.get("cpu_usage_percent", 0)
    mem    = metrics.get("memory_usage_percent", 0)
    err    = metrics.get("error_rate_percent", 0)
    rps    = metrics.get("requests_per_second", 0)
    lat    = metrics.get("request_latency_p99", metrics.get("latency_ms", 0))

    # High errors + low RPS → crash → restart
    if err > 30 and rps < 5:
        return "restart"

    # High CPU + high memory + high latency → overload → scale up
    if cpu > 75 and mem > 70 and lat > 500:
        return "scale_up"

    # High errors + normal/low latency → bad deployment → rollback
    if err > 20 and lat < 200:
        return "rollback"

    # Default: restart
    return "restart"


def verify_recovery(service: str, original_score: float) -> bool:
    """Wait VERIFY_WAIT_SEC then check if anomaly score has normalized."""
    log.info(f"Waiting {VERIFY_WAIT_SEC}s to verify recovery for {service}...")
    time.sleep(VERIFY_WAIT_SEC)
    try:
        # We'd query the inference server's last known score for this service
        # For now, check the /health endpoint of the service itself
        resp = requests.get(f"http://{service}:8000/health", timeout=5)
        if resp.status_code == 200:
            log.info(f"{service} health check passed — recovery confirmed")
            return True
    except Exception:
        pass
    log.warning(f"{service} health check failed after remediation")
    return False


def handle_alert(alert: dict):
    service = alert.get("service", "unknown")
    score   = alert.get("anomaly_score", 0.0)
    log.info(f"Processing alert: service={service} score={score:.4f}")

    action = classify_anomaly(alert)
    log.info(f"Classified action: {action} for {service}")

    success = False
    if action == "restart":
        success = restart_pod(service)
        reason = "High error rate with low RPS — suspected crash"
    elif action == "scale_up":
        success = scale_up(service)
        reason = "High CPU/memory/latency — suspected overload"
    elif action == "rollback":
        success = rollback(service)
        reason = "High errors with normal latency — suspected bad deployment"
    else:
        reason = "Unknown pattern"

    result = "success" if success else "failed"
    audit(action, service, reason, result, alert)

    if success:
        recovered = verify_recovery(service, score)
        if recovered:
            audit("verify_recovery", service, "Post-remediation health check", "recovered", alert)
        else:
            escalate(service, alert, f"Service did not recover after {action}. Manual intervention required.")
            audit("escalate", service, "Recovery verification failed", "escalated", alert)
    else:
        escalate(service, alert, f"Remediation action '{action}' failed to execute.")


def run():
    consumer = KafkaConsumer(
        ALERTS_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        auto_offset_reset="latest",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        group_id="remediation-engine",
    )
    log.info(f"Remediation engine listening on '{ALERTS_TOPIC}'")

    for msg in consumer:
        alert = msg.value
        try:
            handle_alert(alert)
        except Exception as e:
            log.error(f"Unhandled error processing alert: {e}", exc_info=True)


if __name__ == "__main__":
    run()
