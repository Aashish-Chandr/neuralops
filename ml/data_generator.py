"""
Synthetic metric data generator.

Real training data is better (see scripts/collect_real_data.py), but you need
hours of running services to get enough of it. This gets you started immediately
and produces realistic-enough distributions for the model to learn from.

The normal distribution is based on what I've seen in actual microservice metrics:
- CPU: 15-35% at steady state, sinusoidal diurnal pattern
- Memory: 30-50%, slow drift upward then GC kicks in
- Latency: 60-120ms p99 for a simple service, spikes with load
- Error rate: <2% is normal, anything above 5% is worth looking at
- RPS: varies a lot, but the shape matters more than the absolute value

Anomaly types are based on the failure modes I've actually seen:
- cpu_spike: runaway loop, bad query, memory pressure causing GC thrashing
- memory_leak: classic — gradual climb until OOM or restart
- latency_spike: downstream dependency slow, connection pool exhausted
- error_burst: bad deploy, config change, dependency outage
- crash: process dies, RPS drops to zero, errors spike briefly then silence
"""
import numpy as np


def generate_normal(n_samples: int = 5000, seq_len: int = 60, seed: int = 42) -> np.ndarray:
    rng = np.random.default_rng(seed)
    sequences = []

    for _ in range(n_samples):
        t = np.arange(seq_len)

        # sinusoidal components simulate diurnal patterns and natural oscillation
        cpu     = 20 + 10 * np.sin(t / 20) + rng.normal(0, 3, seq_len)
        memory  = 35 + 5  * np.sin(t / 30) + rng.normal(0, 2, seq_len)
        latency = 80 + 20 * np.sin(t / 15) + rng.normal(0, 10, seq_len)
        err     = rng.uniform(0, 2, seq_len)
        rps     = 50 + 20 * np.sin(t / 25) + rng.normal(0, 5, seq_len)

        seq = np.stack([
            np.clip(cpu,     5,   95),
            np.clip(memory,  10,  95),
            np.clip(latency, 10,  2000),
            np.clip(err,     0,   100),
            np.clip(rps,     1,   500),
        ], axis=1)
        sequences.append(seq)

    return np.array(sequences, dtype=np.float32)


def generate_anomalous(n_samples: int = 1000, seq_len: int = 60, seed: int = 99) -> np.ndarray:
    """
    NOT used for training. Only for threshold calibration and evaluation.

    The anomaly onset is at seq_len // 2 so the first half looks normal —
    this tests whether the model catches the transition, not just sustained
    anomalous state.
    """
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

        onset = seq_len // 2

        if atype == "cpu_spike":
            cpu[onset:] += rng.uniform(50, 75)
        elif atype == "memory_leak":
            # linear ramp is more realistic than a step function
            memory[onset:] += np.linspace(0, 55, seq_len - onset)
        elif atype == "latency_spike":
            latency[onset:] += rng.uniform(500, 1500)
        elif atype == "error_burst":
            err[onset:] = rng.uniform(30, 60, seq_len - onset)
        elif atype == "crash":
            rps[onset:] = rng.uniform(0, 2, seq_len - onset)
            err[onset:] = rng.uniform(40, 80, seq_len - onset)

        seq = np.stack([
            np.clip(cpu,     5,   100),
            np.clip(memory,  10,  100),
            np.clip(latency, 10,  5000),
            np.clip(err,     0,   100),
            np.clip(rps,     0,   500),
        ], axis=1)
        sequences.append(seq)

    return np.array(sequences, dtype=np.float32)


def normalize(data: np.ndarray, stats: dict | None = None) -> tuple[np.ndarray, dict]:
    """
    Min-max normalization. Pass stats from training data when normalizing
    validation/test/inference data — you want the same scale, not a new one.
    """
    if stats is None:
        flat = data.reshape(-1, data.shape[-1])
        stats = {"min": flat.min(axis=0), "max": flat.max(axis=0)}

    denom = stats["max"] - stats["min"]
    denom[denom == 0] = 1.0  # avoid divide-by-zero for constant features

    return ((data - stats["min"]) / denom).astype(np.float32), stats
