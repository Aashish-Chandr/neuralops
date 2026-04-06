"""
Integration test: full flow from metric sequence → inference → anomaly alert.
Tests the inference server logic without requiring a running server.
"""
import sys, os
import json
import numpy as np
import torch
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "ml"))
from model import LSTMAutoencoder
from data_generator import generate_normal, generate_anomalous, normalize


@pytest.fixture(scope="module")
def trained_model():
    """Quick-train a model for integration testing."""
    model = LSTMAutoencoder(input_size=5, hidden_size=32, num_layers=1, latent_size=8, seq_len=60)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)

    normal = generate_normal(n_samples=300, seq_len=60)
    normal_norm, stats = normalize(normal)
    data = torch.tensor(normal_norm)

    model.train()
    for _ in range(10):
        optimizer.zero_grad()
        loss = torch.mean((model(data[:32]) - data[:32]) ** 2)
        loss.backward()
        optimizer.step()

    model.eval()
    errors = model.reconstruction_error(data).numpy()
    threshold = float(np.percentile(errors, 95))
    return model, threshold, stats


def test_normal_sequence_below_threshold(trained_model):
    model, threshold, stats = trained_model
    normal = generate_normal(n_samples=50, seq_len=60)
    normal_norm, _ = normalize(normal, stats=stats)
    errors = model.reconstruction_error(torch.tensor(normal_norm)).numpy()
    # At least 80% of normal sequences should be below threshold
    below = (errors < threshold).mean()
    assert below >= 0.80, f"Only {below:.0%} of normal sequences below threshold"


def test_anomalous_sequence_above_threshold(trained_model):
    model, threshold, stats = trained_model
    anomaly = generate_anomalous(n_samples=50, seq_len=60)
    anomaly_norm, _ = normalize(anomaly, stats=stats)
    errors = model.reconstruction_error(torch.tensor(anomaly_norm)).numpy()
    # At least 50% of anomalous sequences should be above threshold
    above = (errors > threshold).mean()
    assert above >= 0.50, f"Only {above:.0%} of anomalous sequences above threshold"


def test_inference_response_structure(trained_model):
    """Simulate what inference_server.py /predict returns."""
    model, threshold, stats = trained_model

    seq = generate_normal(n_samples=1, seq_len=60)[0]
    seq_norm, _ = normalize(seq[np.newaxis], stats=stats)
    tensor = torch.tensor(seq_norm)

    score = float(model.reconstruction_error(tensor).item())
    is_anomaly = score > threshold

    with torch.no_grad():
        recon = model(tensor).squeeze(0).numpy()
    feature_errors = np.mean((seq_norm[0] - recon) ** 2, axis=0)
    feature_names = ["cpu_usage_percent", "memory_usage_percent", "latency_ms",
                     "error_rate_percent", "rps"]
    top_features = dict(zip(feature_names, feature_errors.tolist()))

    response = {
        "service": "payment-service",
        "anomaly_score": score,
        "is_anomaly": is_anomaly,
        "threshold": threshold,
        "top_features": top_features,
    }

    assert "anomaly_score" in response
    assert "is_anomaly" in response
    assert isinstance(response["is_anomaly"], bool)
    assert len(response["top_features"]) == 5
    assert all(v >= 0 for v in response["top_features"].values())
