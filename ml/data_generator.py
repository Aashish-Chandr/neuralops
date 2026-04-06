"""
Generates synthetic training data simulating normal and anomalous microservice metrics.
Features per timestep: [cpu%, memory%, latency_ms, error_rate%, rps]
"""
import numpy as np
import pandas as pd


def generate_normal(n_samples: int = 5000, seq_len: int = 60, seed: int = 42) -> np.ndarray:
    """Generate normal operating metric sequences."""
    rng = np.random.default_rng(seed)
    sequences = []
    for _ in range(n_samples):
        t = np.arange(seq_len)
        cpu     = 20 + 10 * np.sin(t / 20) + rng.normal(0, 3, seq_len)
        memory  = 35 + 5  * np.sin(t / 30) + rng.normal(0, 2, seq_len)
        latency = 80 + 20 * np.sin(t / 15) + rng.normal(0, 10, seq_len)
        err     = rng.uniform(0, 2, seq_len)
        rps     = 50 + 20 * np.sin(t / 25) + rng.normal(0, 5, seq_len)

        seq = np.stack([
            np.clip(cpu, 5, 95),
            np.clip(memory, 10, 95),
            np.clip(latency, 10, 2000),
            np.clip(err, 0, 100),
            np.clip(rps, 1, 500),
        ], axis=1)
        sequences.append(seq)
    return np.array(sequences, dtype=np.float32)


def generate_anomalous(n_samples: int = 1000, seq_len: int = 60, seed: int = 99) -> np.ndarray:
    """Generate anomalous metric sequences (NOT used for training, only evaluation)."""
    rng = np.random.default_rng(seed)
    sequences = []
    anomaly_types = ["cpu_spike", "memory_leak", "latency_spike", "error_burst", "crash"]

    for i in range(n_samples):
        atype = anomaly_types[i % len(anomaly_types)]
        t = np.arange(seq_len)
        cpu     = 20 + rng.normal(0, 3, seq_len)
        memory  = 35 + rng.normal(0, 2, seq_len)
        latency = 80 + rng.normal(0, 10, seq_len)
        err     = rng.uniform(0, 2, seq_len)
        rps     = 50 + rng.normal(0, 5, seq_len)

        onset = seq_len // 2  # anomaly starts halfway through
        if atype == "cpu_spike":
            cpu[onset:] += rng.uniform(50, 75)
        elif atype == "memory_leak":
            memory[onset:] += np.linspace(0, 55, seq_len - onset)
        elif atype == "latency_spike":
            latency[onset:] += rng.uniform(500, 1500)
        elif atype == "error_burst":
            err[onset:] = rng.uniform(30, 60, seq_len - onset)
        elif atype == "crash":
            rps[onset:] = rng.uniform(0, 2, seq_len - onset)
            err[onset:] = rng.uniform(40, 80, seq_len - onset)

        seq = np.stack([
            np.clip(cpu, 5, 100),
            np.clip(memory, 10, 100),
            np.clip(latency, 10, 5000),
            np.clip(err, 0, 100),
            np.clip(rps, 0, 500),
        ], axis=1)
        sequences.append(seq)
    return np.array(sequences, dtype=np.float32)


def normalize(data: np.ndarray, stats: dict | None = None) -> tuple[np.ndarray, dict]:
    """Min-max normalize. Returns normalized data and stats dict for reuse."""
    if stats is None:
        stats = {
            "min": data.reshape(-1, data.shape[-1]).min(axis=0),
            "max": data.reshape(-1, data.shape[-1]).max(axis=0),
        }
    denom = stats["max"] - stats["min"]
    denom[denom == 0] = 1.0
    normalized = (data - stats["min"]) / denom
    return normalized.astype(np.float32), stats
