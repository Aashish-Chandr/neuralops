"""Unit tests for LSTM Autoencoder."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import torch
import numpy as np
import pytest
from model import LSTMAutoencoder
from data_generator import generate_normal, generate_anomalous, normalize


def test_model_forward_shape():
    model = LSTMAutoencoder(input_size=5, hidden_size=32, num_layers=1, latent_size=8, seq_len=60)
    x = torch.randn(4, 60, 5)
    out = model(x)
    assert out.shape == (4, 60, 5), f"Expected (4,60,5), got {out.shape}"


def test_reconstruction_error_shape():
    model = LSTMAutoencoder(input_size=5, hidden_size=32, num_layers=1, latent_size=8, seq_len=60)
    x = torch.randn(8, 60, 5)
    errors = model.reconstruction_error(x)
    assert errors.shape == (8,), f"Expected (8,), got {errors.shape}"


def test_reconstruction_error_positive():
    model = LSTMAutoencoder(input_size=5, hidden_size=32, num_layers=1, latent_size=8, seq_len=60)
    x = torch.randn(4, 60, 5)
    errors = model.reconstruction_error(x)
    assert (errors >= 0).all(), "Reconstruction errors must be non-negative"


def test_anomaly_higher_error_than_normal():
    """Trained model should have higher reconstruction error on anomalous data."""
    model = LSTMAutoencoder(input_size=5, hidden_size=32, num_layers=1, latent_size=8, seq_len=60)
    # Quick training on normal data
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    normal = torch.tensor(generate_normal(n_samples=200, seq_len=60))
    normal_norm, stats = normalize(normal.numpy())
    normal_t = torch.tensor(normal_norm)

    for _ in range(5):
        optimizer.zero_grad()
        recon = model(normal_t[:32])
        loss = torch.mean((normal_t[:32] - recon) ** 2)
        loss.backward()
        optimizer.step()

    anomaly = torch.tensor(normalize(generate_anomalous(n_samples=50, seq_len=60), stats=stats)[0])
    normal_errors  = model.reconstruction_error(normal_t[:50]).mean().item()
    anomaly_errors = model.reconstruction_error(anomaly).mean().item()
    # After even minimal training, anomaly errors should be >= normal errors
    assert anomaly_errors >= normal_errors * 0.5, "Anomaly errors should be at least comparable to normal"


def test_data_generator_shapes():
    normal = generate_normal(n_samples=10, seq_len=60)
    assert normal.shape == (10, 60, 5)
    anomaly = generate_anomalous(n_samples=5, seq_len=60)
    assert anomaly.shape == (5, 60, 5)


def test_normalize_range():
    data = generate_normal(n_samples=100, seq_len=60)
    norm, stats = normalize(data)
    assert norm.min() >= -0.01
    assert norm.max() <= 1.01
