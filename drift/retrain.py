"""
Automated retraining pipeline.
Called by drift_detector.py when drift is detected.
Retrains model, evaluates against holdout, promotes if better.
"""
import os
import sys
import json
import logging
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset, random_split
import mlflow
import mlflow.pytorch
from mlflow.tracking import MlflowClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ml"))
from model import LSTMAutoencoder
from data_generator import generate_normal, generate_anomalous, normalize

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("retrain")

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
MODEL_NAME          = os.getenv("MODEL_NAME", "neuralops-lstm-autoencoder")
EPOCHS              = int(os.getenv("RETRAIN_EPOCHS", "30"))
BATCH               = int(os.getenv("RETRAIN_BATCH",  "64"))
LR                  = float(os.getenv("RETRAIN_LR",   "0.001"))


def get_current_production_f1(client: MlflowClient) -> float:
    try:
        versions = client.get_latest_versions(MODEL_NAME, stages=["Production"])
        if versions:
            run = client.get_run(versions[0].run_id)
            return float(run.data.metrics.get("f1_score", 0.0))
    except Exception as e:
        log.warning(f"Could not fetch production model metrics: {e}")
    return 0.0


def main():
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    client = MlflowClient()
    device = torch.device("cpu")

    current_f1 = get_current_production_f1(client)
    log.info(f"Current production F1: {current_f1:.4f}")

    # Generate fresh training data
    normal_data  = generate_normal(n_samples=5000, seq_len=60, seed=int(os.getenv("SEED", "42")))
    anomaly_data = generate_anomalous(n_samples=1000, seq_len=60)
    normal_norm, stats = normalize(normal_data)
    anomaly_norm, _    = normalize(anomaly_data, stats=stats)

    tensor_data = torch.tensor(normal_norm)
    val_size    = int(0.1 * len(tensor_data))
    train_ds, val_ds = random_split(
        TensorDataset(tensor_data),
        [len(tensor_data) - val_size, val_size]
    )
    train_loader = DataLoader(train_ds, batch_size=BATCH, shuffle=True)
    val_loader   = DataLoader(val_ds,   batch_size=BATCH)

    model     = LSTMAutoencoder(input_size=5, hidden_size=64, num_layers=2, latent_size=16, seq_len=60).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    criterion = nn.MSELoss()
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)

    mlflow.set_experiment("neuralops-anomaly-detection")
    with mlflow.start_run(run_name="auto-retrain"):
        mlflow.log_params({"epochs": EPOCHS, "lr": LR, "batch": BATCH, "trigger": "drift_detected"})

        best_val_loss = float("inf")
        for epoch in range(1, EPOCHS + 1):
            # Train
            model.train()
            train_loss = 0.0
            for (batch,) in train_loader:
                batch = batch.to(device)
                optimizer.zero_grad()
                loss = criterion(model(batch), batch)
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                train_loss += loss.item()
            train_loss /= len(train_loader)

            # Validate
            model.eval()
            val_loss = 0.0
            with torch.no_grad():
                for (batch,) in val_loader:
                    val_loss += criterion(model(batch.to(device)), batch.to(device)).item()
            val_loss /= len(val_loader)
            scheduler.step(val_loss)

            mlflow.log_metrics({"train_loss": train_loss, "val_loss": val_loss}, step=epoch)
            if epoch % 10 == 0:
                log.info(f"Epoch {epoch:3d}/{EPOCHS} | train={train_loss:.6f} | val={val_loss:.6f}")

            if val_loss < best_val_loss:
                best_val_loss = val_loss

        # Threshold calibration
        model.eval()
        normal_errors  = model.reconstruction_error(torch.tensor(normal_norm)).numpy()
        anomaly_errors = model.reconstruction_error(torch.tensor(anomaly_norm)).numpy()
        threshold = float(np.percentile(normal_errors, 95))

        tp = int((anomaly_errors > threshold).sum())
        fp = int((normal_errors  > threshold).sum())
        fn = int((anomaly_errors <= threshold).sum())
        precision = tp / (tp + fp + 1e-9)
        recall    = tp / (tp + fn + 1e-9)
        new_f1    = 2 * precision * recall / (precision + recall + 1e-9)

        mlflow.log_metrics({
            "f1_score": new_f1, "threshold": threshold,
            "val_loss": best_val_loss, "precision": precision, "recall": recall,
        })
        log.info(f"New model F1={new_f1:.4f} | Current production F1={current_f1:.4f}")

        if new_f1 > current_f1:
            log.info("New model is better — registering and promoting to Production")
            result = mlflow.pytorch.log_model(
                model,
                artifact_path="model",
                registered_model_name=MODEL_NAME,
            )
            # Get the version that was just registered
            versions = client.search_model_versions(f"name='{MODEL_NAME}'")
            latest_version = max(int(v.version) for v in versions)
            client.transition_model_version_stage(
                name=MODEL_NAME,
                version=str(latest_version),
                stage="Production",
                archive_existing_versions=True,
            )
            log.info(f"Model v{latest_version} promoted to Production")
        else:
            log.info("New model did not improve — keeping current production model")


if __name__ == "__main__":
    main()
