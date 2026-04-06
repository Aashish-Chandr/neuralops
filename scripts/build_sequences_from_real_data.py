"""
Converts collected real JSONL data into numpy sequence arrays for training.
Usage: python scripts/build_sequences_from_real_data.py
"""
import os, json, glob
import numpy as np

DATA_DIR  = os.path.join(os.path.dirname(__file__), "..", "data", "real")
OUT_DIR   = os.path.join(os.path.dirname(__file__), "..", "data")
SEQ_LEN   = 60
FEATURES  = ["cpu_usage_percent", "memory_usage_percent", "latency_p99_ms",
             "error_rate_percent", "requests_per_second"]
SERVICES  = ["user-service", "order-service", "payment-service", "inventory-service", "notification-service"]


def load_jsonl(path: str) -> list:
    with open(path) as f:
        return [json.loads(l) for l in f if l.strip()]


def build_sequences(snapshots: list, label: str) -> np.ndarray:
    """Slide a window of SEQ_LEN over each service's time series."""
    sequences = []
    for svc in SERVICES:
        readings = []
        for snap in snapshots:
            svc_data = snap.get("services", {}).get(svc, {})
            readings.append([svc_data.get(f, 0.0) for f in FEATURES])

        # Sliding window
        for i in range(len(readings) - SEQ_LEN + 1):
            sequences.append(readings[i:i + SEQ_LEN])

    return np.array(sequences, dtype=np.float32)


def main():
    normal_files  = glob.glob(os.path.join(DATA_DIR, "normal_*.jsonl"))
    anomaly_files = glob.glob(os.path.join(DATA_DIR, "anomaly_*.jsonl"))

    if not normal_files:
        print("No real data found. Run: python scripts/collect_real_data.py --label normal")
        return

    print(f"Found {len(normal_files)} normal files, {len(anomaly_files)} anomaly files")

    normal_snaps  = [s for f in normal_files  for s in load_jsonl(f)]
    anomaly_snaps = [s for f in anomaly_files for s in load_jsonl(f)]

    normal_seqs  = build_sequences(normal_snaps,  "normal")
    anomaly_seqs = build_sequences(anomaly_snaps, "anomaly") if anomaly_snaps else np.zeros((0, SEQ_LEN, 5))

    print(f"Normal sequences:  {normal_seqs.shape}")
    print(f"Anomaly sequences: {anomaly_seqs.shape}")

    np.save(os.path.join(OUT_DIR, "real_normal_sequences.npy"),  normal_seqs)
    if len(anomaly_seqs) > 0:
        np.save(os.path.join(OUT_DIR, "real_anomaly_sequences.npy"), anomaly_seqs)

    print("Saved. Train with: python ml/train.py")


if __name__ == "__main__":
    main()
