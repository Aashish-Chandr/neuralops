"""
Train LSTM Autoencoder for anomaly detection.
Logs everything to MLflow and registers the best model.

Usage:
    python train.py [--epochs 50] [--lr 0.001] [--hidden 64] [--latent 16]
"""
import argparse
import json
import os
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset, random_split
import mlflow
import mlflow.pytorch

from model import LSTMAutoencoder
from data_generator import generate_normal, generate_anomalous, normalize


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--epochs",    type=int,   default=50)
    p.add_argument("--lr",        type=float, default=0.001)
    p.add_argument("--hidden",    type=int,   default=64)
    p.add_argument("--latent",    type=int,   default=16)
    p.add_argument("--seq-len",   type=int,   default=60)
    p.add_argument("--batch",     type=int,   default=64)
    p.add_argument("--threshold-percentile", type=float, default=95.0)
    return p.parse_args()


def train():
    args = parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training on {device}")

    # --- Data ---
    print("Generating training data...")
    normal_data = generate_normal(n_samples=5000, seq_len=args.seq_len)
    anomaly_data = generate_anomalous(n_samples=1000, seq_len=args.seq_len)
    normal_norm, stats = normalize(normal_data)
    anomaly_norm, _    = normalize(anomaly_data, stats=stats)

    # Save normalization stats for inference
    os.makedirs("artifacts", exist_ok=True)
    with open("artifacts/norm_stats.json", "w") as f:
        json.dump({"min": stats["min"].tolist(), "max": stats["max"].tolist()}, f)

    tensor_data = torch.tensor(normal_norm)
    val_size = int(0.1 * len(tensor_data))
    train_ds, val_ds = random_split(TensorDataset(tensor_data), [len(tensor_data) - val_size, val_size])
    train_loader = DataLoader(train_ds, batch_size=args.batch, shuffle=True)
    val_loader   = DataLoader(val_ds,   batch_size=args.batch)

    # --- Model ---
    model = LSTMAutoencoder(
        input_size=5,
        hidden_size=args.hidden,
        num_layers=2,
        latent_size=args.latent,
        seq_len=args.seq_len,
    ).to(device)

    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    criterion = nn.MSELoss()
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)

    mlflow.set_experiment("neuralops-anomaly-detection")

    with mlflow.start_run(run_name=f"lstm-ae-h{args.hidden}-l{args.latent}"):
        mlflow.log_params({
            "epochs": args.epochs, "lr": args.lr, "hidden_size": args.hidden,
            "latent_size": args.latent, "seq_len": args.seq_len, "batch_size": args.batch,
            "threshold_percentile": args.threshold_percentile,
        })

        best_val_loss = float("inf")
        for epoch in range(1, args.epochs + 1):
            # Train
            model.train()
            train_loss = 0.0
            for (batch,) in train_loader:
                batch = batch.to(device)
                optimizer.zero_grad()
                recon = model(batch)
                loss = criterion(recon, batch)
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
                    batch = batch.to(device)
                    recon = model(batch)
                    val_loss += criterion(recon, batch).item()
            val_loss /= len(val_loader)
            scheduler.step(val_loss)

            mlflow.log_metrics({"train_loss": train_loss, "val_loss": val_loss}, step=epoch)
            if epoch % 10 == 0:
                print(f"Epoch {epoch:3d}/{args.epochs} | train={train_loss:.6f} | val={val_loss:.6f}")

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                torch.save(model.state_dict(), "artifacts/best_model.pt")

        # --- Threshold calibration ---
        print("Calibrating anomaly threshold...")
        model.load_state_dict(torch.load("artifacts/best_model.pt", map_location=device))
        model.eval()

        normal_tensor  = torch.tensor(normal_norm).to(device)
        anomaly_tensor = torch.tensor(anomaly_norm).to(device)

        normal_errors  = model.reconstruction_error(normal_tensor).cpu().numpy()
        anomaly_errors = model.reconstruction_error(anomaly_tensor).cpu().numpy()

        threshold = float(np.percentile(normal_errors, args.threshold_percentile))
        print(f"Threshold (p{args.threshold_percentile:.0f} of normal errors): {threshold:.6f}")

        # Evaluate
        tp = int((anomaly_errors > threshold).sum())
        fp = int((normal_errors  > threshold).sum())
        tn = int((normal_errors  <= threshold).sum())
        fn = int((anomaly_errors <= threshold).sum())
        precision = tp / (tp + fp + 1e-9)
        recall    = tp / (tp + fn + 1e-9)
        f1        = 2 * precision * recall / (precision + recall + 1e-9)

        mlflow.log_metrics({
            "threshold": threshold,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "best_val_loss": best_val_loss,
        })

        print(f"Precision={precision:.3f} | Recall={recall:.3f} | F1={f1:.3f}")

        # Save threshold
        with open("artifacts/threshold.json", "w") as f:
            json.dump({"threshold": threshold}, f)

        # Log artifacts
        mlflow.log_artifacts("artifacts")

        # Log and register model
        mlflow.pytorch.log_model(
            model,
            artifact_path="model",
            registered_model_name="neuralops-lstm-autoencoder",
        )
        print("Model registered in MLflow Model Registry.")


if __name__ == "__main__":
    train()
