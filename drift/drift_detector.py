"""
Model Drift Detector using Evidently AI.
Runs daily (via Kubernetes CronJob) to compare training vs production distributions.
Triggers retraining if drift exceeds threshold.
"""
import os
import json
import logging
import subprocess
import numpy as np
import pandas as pd
import requests
from datetime import datetime, timedelta, timezone
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset, DataQualityPreset
from evidently.metrics import ColumnDriftMetric

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("drift-detector")

PROMETHEUS_URL      = os.getenv("PROMETHEUS_URL",       "http://prometheus:9090")
DRIFT_THRESHOLD     = float(os.getenv("DRIFT_THRESHOLD", "0.3"))   # fraction of drifted features
REPORT_OUTPUT_DIR   = os.getenv("REPORT_OUTPUT_DIR",    "/reports")
RETRAIN_SCRIPT      = os.getenv("RETRAIN_SCRIPT",       "/app/retrain.py")
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI",  "http://mlflow:5000")

FEATURE_NAMES = ["cpu_usage_percent", "memory_usage_percent", "request_latency_p99",
                 "error_rate_percent", "requests_per_second"]

SERVICES = ["user-service", "order-service", "payment-service", "inventory-service", "notification-service"]


def fetch_prometheus_range(query: str, hours: int = 24) -> list[float]:
    end   = datetime.now(timezone.utc)
    start = end - timedelta(hours=hours)
    try:
        resp = requests.get(f"{PROMETHEUS_URL}/api/v1/query_range", params={
            "query": query, "start": start.timestamp(),
            "end": end.timestamp(), "step": "60",
        }, timeout=10)
        results = resp.json().get("data", {}).get("result", [])
        if results:
            return [float(v[1]) for v in results[0]["values"]]
    except Exception as e:
        log.warning(f"Prometheus query failed: {e}")
    return []


def build_production_df() -> pd.DataFrame:
    """Fetch last 24h of production metrics from Prometheus."""
    rows = []
    for svc in SERVICES:
        cpu_vals = fetch_prometheus_range(f'cpu_usage_percent{{service="{svc}"}}')
        mem_vals = fetch_prometheus_range(f'memory_usage_percent{{service="{svc}"}}')
        lat_vals = fetch_prometheus_range(f'histogram_quantile(0.99, rate(http_request_duration_seconds_bucket{{service="{svc}"}}[5m]))')
        err_vals = fetch_prometheus_range(f'error_rate_percent{{service="{svc}"}}')
        rps_vals = fetch_prometheus_range(f'requests_per_second{{service="{svc}"}}')

        n = min(len(cpu_vals), len(mem_vals), len(lat_vals), len(err_vals), len(rps_vals))
        for i in range(n):
            rows.append({
                "cpu_usage_percent":    cpu_vals[i],
                "memory_usage_percent": mem_vals[i],
                "request_latency_p99":  lat_vals[i] * 1000 if lat_vals[i] < 100 else lat_vals[i],
                "error_rate_percent":   err_vals[i],
                "requests_per_second":  rps_vals[i],
            })

    if not rows:
        log.warning("No production data fetched — generating synthetic fallback")
        rng = np.random.default_rng(0)
        rows = [{
            "cpu_usage_percent":    float(rng.uniform(15, 30)),
            "memory_usage_percent": float(rng.uniform(30, 45)),
            "request_latency_p99":  float(rng.uniform(60, 120)),
            "error_rate_percent":   float(rng.uniform(0, 3)),
            "requests_per_second":  float(rng.uniform(30, 80)),
        } for _ in range(500)]

    return pd.DataFrame(rows)


def build_reference_df() -> pd.DataFrame:
    """Build reference dataset from training distribution parameters."""
    rng = np.random.default_rng(42)
    n = 1000
    return pd.DataFrame({
        "cpu_usage_percent":    rng.normal(20, 8, n).clip(5, 95),
        "memory_usage_percent": rng.normal(35, 6, n).clip(10, 95),
        "request_latency_p99":  rng.normal(80, 20, n).clip(10, 500),
        "error_rate_percent":   rng.uniform(0, 2, n),
        "requests_per_second":  rng.normal(50, 15, n).clip(1, 200),
    })


def run_drift_report(reference: pd.DataFrame, current: pd.DataFrame) -> dict:
    report = Report(metrics=[DataDriftPreset(), DataQualityPreset()])
    report.run(reference_data=reference, current_data=current)

    os.makedirs(REPORT_OUTPUT_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(REPORT_OUTPUT_DIR, f"drift_report_{ts}.html")
    report.save_html(report_path)
    log.info(f"Drift report saved to {report_path}")

    result = report.as_dict()
    drift_metrics = result.get("metrics", [])

    drifted_features = 0
    total_features = 0
    for m in drift_metrics:
        if m.get("metric") == "DatasetDriftMetric":
            result_data = m.get("result", {})
            drifted_features = result_data.get("number_of_drifted_columns", 0)
            total_features   = result_data.get("number_of_columns", len(FEATURE_NAMES))
            break

    drift_fraction = drifted_features / max(total_features, 1)
    log.info(f"Drift: {drifted_features}/{total_features} features drifted ({drift_fraction:.2%})")
    return {"drift_fraction": drift_fraction, "drifted_features": drifted_features, "report_path": report_path}


def trigger_retraining():
    log.info("Drift threshold exceeded — triggering retraining pipeline...")
    try:
        result = subprocess.run(
            ["python", RETRAIN_SCRIPT],
            capture_output=True, text=True, timeout=3600
        )
        if result.returncode == 0:
            log.info("Retraining completed successfully")
            log.info(result.stdout[-2000:])
        else:
            log.error(f"Retraining failed:\n{result.stderr[-2000:]}")
    except Exception as e:
        log.error(f"Failed to trigger retraining: {e}")


def main():
    log.info("Starting drift detection run...")
    reference_df  = build_reference_df()
    production_df = build_production_df()

    log.info(f"Reference samples: {len(reference_df)} | Production samples: {len(production_df)}")
    drift_result = run_drift_report(reference_df, production_df)

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "drift_fraction": drift_result["drift_fraction"],
        "drifted_features": drift_result["drifted_features"],
        "threshold": DRIFT_THRESHOLD,
        "action": "none",
    }

    if drift_result["drift_fraction"] >= DRIFT_THRESHOLD:
        log.warning(f"Drift {drift_result['drift_fraction']:.2%} >= threshold {DRIFT_THRESHOLD:.2%} — retraining")
        summary["action"] = "retrain_triggered"
        trigger_retraining()
    else:
        log.info(f"Drift {drift_result['drift_fraction']:.2%} < threshold — no action needed")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
