"""
Auto-remediation engine. Consumes anomaly alerts and takes action in Kubernetes.

The rule-based classifier is intentionally simple. I considered training a
classifier to pick the action, but you'd need labeled historical incidents to
train it, and the rules are actually pretty reliable:
- High errors + low RPS almost always means the process crashed
- High CPU + memory + latency almost always means it's overloaded
- High errors + normal latency almost always means a bad deploy

The verify_recovery step is important. Without it, you'd have no idea if the
action actually worked. If recovery fails, we escalate to Slack rather than
retrying automatically — automated retry loops on failed remediations can make
things significantly worse (e.g. repeatedly restarting a pod that crashes on
startup due to a config error).

Every action is written to a JSONL audit log. This is non-negotiable for any
automated system that touches production infrastructure. You need to be able to
answer "what did the system do and when" after an incident.
"""
import os
import json
import time
import logging
import requests
from datetime import datetime, timezone
from kafka import KafkaConsumer
from kubernetes import client, config

log = logging.getLogger("remediation-engine")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

KAFKA_BOOTSTRAP   = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
ALERTS_TOPIC      = os.getenv("KAFKA_ALERTS_TOPIC",      "anomaly-alerts")
K8S_NAMESPACE     = os.getenv("K8S_NAMESPACE",           "neuralops")
SLACK_WEBHOOK     = os.getenv("SLACK_WEBHOOK_URL",       "")
VERIFY_WAIT_SEC   = int(os.getenv("VERIFY_WAIT_SECONDS", "300"))
SCALE_UP_REPLICAS = int(os.getenv("SCALE_UP_REPLICAS",   "3"))
AUDIT_LOG_PATH    = os.getenv("AUDIT_LOG_PATH", "/var/log/neuralops/remediation_audit.jsonl")
KAFKA_SASL_USERNAME = os.getenv("KAFKA_SASL_USERNAME", "")
KAFKA_SASL_PASSWORD = os.getenv("KAFKA_SASL_PASSWORD", "")


def load_k8s():
    try:
        config.load_incluster_config()
        log.info("using in-cluster kubeconfig")
    except Exception:
        try:
            config.load_kube_config()
            log.info("using local kubeconfig")
        except Exception as e:
            log.warning(f"no k8s config ({e}) — actions will be simulated")
            return None, None
    return client.CoreV1Api(), client.AppsV1Api()


core_api, apps_api = load_k8s()


def audit(action: str, service: str, reason: str, result: str, alert: dict):
    entry = {
        "timestamp":    datetime.now(timezone.utc).isoformat(),
        "action":       action,
        "service":      service,
        "reason":       reason,
        "result":       result,
        "anomaly_score": alert.get("anomaly_score"),
        "top_features": alert.get("top_features", {}),
    }
    log.info(f"AUDIT | {action} | {service} | {result} | score={alert.get('anomaly_score', 0):.4f}")
    try:
        os.makedirs(os.path.dirname(AUDIT_LOG_PATH), exist_ok=True)
        with open(AUDIT_LOG_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        log.warning(f"audit write failed: {e}")


def escalate(service: str, alert: dict, message: str):
    log.error(f"ESCALATION | {service} | {message}")
    if not SLACK_WEBHOOK:
        return
    try:
        requests.post(SLACK_WEBHOOK, json={
            "text": (
                f":rotating_light: *NeuralOps escalation*\n"
                f"Service: `{service}`\n"
                f"{message}\n"
                f"Score: {alert.get('anomaly_score', 0):.4f}"
            )
        }, timeout=5)
    except Exception as e:
        log.warning(f"slack webhook failed: {e}")


def restart_pod(service: str) -> bool:
    """Delete the pod. Kubernetes will reschedule it immediately."""
    if core_api is None:
        log.info(f"[sim] restart {service}")
        return True
    try:
        pods = core_api.list_namespaced_pod(
            namespace=K8S_NAMESPACE,
            label_selector=f"app={service}",
        )
        if not pods.items:
            log.warning(f"no pods found for {service}")
            return False
        pod = pods.items[0].metadata.name
        core_api.delete_namespaced_pod(name=pod, namespace=K8S_NAMESPACE)
        log.info(f"deleted {pod} — k8s will restart it")
        return True
    except Exception as e:
        log.error(f"restart failed for {service}: {e}")
        return False


def scale_up(service: str) -> bool:
    if apps_api is None:
        log.info(f"[sim] scale {service} → {SCALE_UP_REPLICAS}")
        return True
    try:
        apps_api.patch_namespaced_deployment_scale(
            name=service,
            namespace=K8S_NAMESPACE,
            body={"spec": {"replicas": SCALE_UP_REPLICAS}},
        )
        log.info(f"scaled {service} to {SCALE_UP_REPLICAS} replicas")
        return True
    except Exception as e:
        log.error(f"scale failed for {service}: {e}")
        return False


def rollback(service: str) -> bool:
    if apps_api is None:
        log.info(f"[sim] rollback {service}")
        return True
    try:
        apps_api.patch_namespaced_deployment(
            name=service,
            namespace=K8S_NAMESPACE,
            body={"spec": {"rollbackTo": {"revision": 0}}},
        )
        log.info(f"rollback triggered for {service}")
        return True
    except Exception as e:
        log.error(f"rollback failed for {service}: {e}")
        return False


def classify_anomaly(alert: dict) -> str:
    m   = alert.get("metrics_snapshot", {})
    cpu = m.get("cpu_usage_percent", 0)
    mem = m.get("memory_usage_percent", 0)
    err = m.get("error_rate_percent", 0)
    rps = m.get("requests_per_second", 0)
    lat = m.get("request_latency_p99", m.get("latency_ms", 0))

    if err > 30 and rps < 5:
        return "restart"       # process is dead or dying

    if cpu > 75 and mem > 70 and lat > 500:
        return "scale_up"      # overloaded, needs more capacity

    if err > 20 and lat < 200:
        return "rollback"      # errors but fast = bad code, not overload

    return "restart"           # default — least destructive option


def verify_recovery(service: str) -> bool:
    log.info(f"waiting {VERIFY_WAIT_SEC}s before checking {service} recovery...")
    time.sleep(VERIFY_WAIT_SEC)
    try:
        resp = requests.get(f"http://{service}:8000/health", timeout=5)
        if resp.status_code == 200:
            log.info(f"{service} recovered")
            return True
    except Exception:
        pass
    log.warning(f"{service} still unhealthy after remediation")
    return False


def handle_alert(alert: dict):
    service = alert.get("service", "unknown")
    score   = alert.get("anomaly_score", 0.0)
    action  = classify_anomaly(alert)

    log.info(f"alert: {service} score={score:.4f} → action={action}")

    reasons = {
        "restart":  "high error rate + low RPS — suspected crash",
        "scale_up": "high CPU/memory/latency — suspected overload",
        "rollback": "high errors + normal latency — suspected bad deploy",
    }

    dispatch = {"restart": restart_pod, "scale_up": scale_up, "rollback": rollback}
    success  = dispatch[action](service)
    result   = "success" if success else "failed"

    audit(action, service, reasons[action], result, alert)

    if not success:
        escalate(service, alert, f"remediation action '{action}' failed to execute")
        return

    if verify_recovery(service):
        audit("verify_recovery", service, "post-remediation health check", "recovered", alert)
    else:
        escalate(service, alert, f"service did not recover after {action} — manual intervention needed")
        audit("escalate", service, "recovery verification failed", "escalated", alert)


def run():
    kafka_kwargs: dict = {
        "auto_offset_reset":  "latest",
        "value_deserializer": lambda m: json.loads(m.decode()),
        "group_id":           "remediation-engine",
    }
    if KAFKA_SASL_USERNAME and KAFKA_SASL_PASSWORD:
        kafka_kwargs.update({
            "security_protocol":   "SASL_SSL",
            "sasl_mechanism":      "PLAIN",
            "sasl_plain_username": KAFKA_SASL_USERNAME,
            "sasl_plain_password": KAFKA_SASL_PASSWORD,
        })
    consumer = KafkaConsumer(ALERTS_TOPIC, bootstrap_servers=KAFKA_BOOTSTRAP, **kafka_kwargs)
    log.info(f"listening on {ALERTS_TOPIC}")

    for msg in consumer:
        try:
            handle_alert(msg.value)
        except Exception as e:
            log.error(f"unhandled error: {e}", exc_info=True)


if __name__ == "__main__":
    run()
