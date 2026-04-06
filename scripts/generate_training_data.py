"""
Generates and saves training data to data/ as CSV files.
Run once before training: python scripts/generate_training_data.py

Outputs:
  data/normal_sequences.npy    — (5000, 60, 5) float32
  data/anomaly_sequences.npy   — (1000, 60, 5) float32
  data/normal_flat.csv         — flattened for inspection
  data/metadata.json           — feature names, shapes, generation params
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ml"))

import json
import numpy as np
import pandas as pd
from data_generator import generate_normal, generate_anomalous, normalize

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)

FEATURE_NAMES = ["cpu_usage_percent", "memory_usage_percent", "latency_p99_ms",
                 "error_rate_percent", "requests_per_second"]

print("Generating normal sequences (5000 × 60 timesteps)...")
normal = generate_normal(n_samples=5000, seq_len=60, seed=42)

print("Generating anomalous sequences (1000 × 60 timesteps)...")
anomaly = generate_anomalous(n_samples=1000, seq_len=60, seed=99)

# Save raw numpy arrays
np.save(os.path.join(DATA_DIR, "normal_sequences.npy"), normal)
np.save(os.path.join(DATA_DIR, "anomaly_sequences.npy"), anomaly)
print(f"Saved normal_sequences.npy  shape={normal.shape}")
print(f"Saved anomaly_sequences.npy shape={anomaly.shape}")

# Save normalization stats
normal_norm, stats = normalize(normal)
np.save(os.path.join(DATA_DIR, "normal_sequences_norm.npy"), normal_norm)
with open(os.path.join(DATA_DIR, "norm_stats.json"), "w") as f:
    json.dump({"min": stats["min"].tolist(), "max": stats["max"].tolist()}, f, indent=2)
print("Saved norm_stats.json")

# Save a flat CSV of the last timestep per sequence for quick inspection
flat = normal[:, -1, :]  # (5000, 5) — last timestep of each sequence
df = pd.DataFrame(flat, columns=FEATURE_NAMES)
df["label"] = "normal"
anomaly_flat = anomaly[:, -1, :]
df_anom = pd.DataFrame(anomaly_flat, columns=FEATURE_NAMES)
df_anom["label"] = "anomaly"
combined = pd.concat([df, df_anom], ignore_index=True)
combined.to_csv(os.path.join(DATA_DIR, "sample_metrics.csv"), index=False)
print(f"Saved sample_metrics.csv ({len(combined)} rows)")

# Metadata
meta = {
    "feature_names": FEATURE_NAMES,
    "normal_shape": list(normal.shape),
    "anomaly_shape": list(anomaly.shape),
    "seq_len": 60,
    "n_features": 5,
    "normal_seed": 42,
    "anomaly_seed": 99,
    "stats": {
        f: {"min": float(stats["min"][i]), "max": float(stats["max"][i])}
        for i, f in enumerate(FEATURE_NAMES)
    },
}
with open(os.path.join(DATA_DIR, "metadata.json"), "w") as f:
    json.dump(meta, f, indent=2)
print("Saved metadata.json")
print("\nDone. Run: python ml/train.py")
