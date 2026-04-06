"""
Collect real metric data from running services via Prometheus.
Run this while services are running to build a real training dataset.

Usage:
  # Start services first
  docker-compose -f docker-compose.full.yml up -d

  # Collect 30 minutes of normal data
  python scripts/collect_real_data.py --duration 1800 --label normal

  # Enable chaos, then collect anomalous data
  python scripts/collect_real_data.py --duration 600 --label anomaly
"""
import argparse
import json
import time
import os
import numpy as np
import requests
from datetime import datetime

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "real")
SERVICES = ["user-service", "order-service", "payment-service", "inventory-service", "notification-service"]

QUERIES = {
    "cpu_usage_percent":    'cpu_usage_percent{{service="{svc}"}}',
    "memory_usage_percent": 'memory_usage_percent{{service="{svc}"}}',
    "latency_p99_ms":       'histogram_quantile(0.99, rate(http_request_duration_seconds_bucket{{service="{svc}"}}[1m])) * 1000',
    "error_rate_percent":   'error_rate_percent{{service="{svc}"}}',
    "requests_per_second":  'requests_per_second{{service="{svc}"}}',
}


def query(q: str) -> float:
    try:
        r = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": q}, timeout=3)
        results = r.json().get("data", {}).get("result", [])
        return float(results[0]["value"][1]) if results else 0.0
    except Exception:
        return 0.0


def collect_snapshot() -> dict:
    snapshot = {"timestamp": time.time(), "services": {}}
    for svc in SERVICES:
        snapshot["services"][svc] = {
            metric: query(q.format(svc=svc))
            for metric, q in QUERIES.items()
        }
    return snapshot


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=int, default=1800, help="Collection duration in seconds")
    parser.add_argument("--interval", type=int, default=15,   help="Scrape interval in seconds")
    parser.add_argument("--label",    type=str, default="normal", choices=["normal", "anomaly"])
    args = parser.parse_args()

    os.makedirs(DATA_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(DATA_DIR, f"{args.label}_{ts}.jsonl")

    n_samples = args.duration // args.interval
    print(f"Collecting {n_samples} snapshots ({args.duration}s) → {out_path}")
    print(f"Label: {args.label}")

    snapshots = []
    with open(out_path, "w") as f:
        for i in range(n_samples):
            snap = collect_snapshot()
            snap["label"] = args.label
            f.write(json.dumps(snap) + "\n")
            snapshots.append(snap)

            if (i + 1) % 10 == 0:
                print(f"  {i+1}/{n_samples} snapshots collected")

            time.sleep(args.interval)

    print(f"\nDone. {len(snapshots)} snapshots saved to {out_path}")
    print("Convert to sequences with: python scripts/build_sequences_from_real_data.py")


if __name__ == "__main__":
    main()
