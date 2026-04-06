"""
Train the LSTM Autoencoder and register it in MLflow.

Usage:
    python train.py
    python train.py --epochs 100 --hidden 128 --latent 32  # bigger model
    python train.py --epochs 10 --hidden 32                # quick sanity check

The threshold calibration at the end is important. Don't skip it.
The 95th percentile of normal reconstruction errors gives ~5% false positive rate,
which is usually acceptable. If you're getting too many false alerts in production,
bump it to 97th or 99th. If you're missing real anomalies, drop it to 90th.
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
    p.add_argument("--epochs",               type=int,   default=50)
    p.add_argument("--lr",                   type=float, default=0.001)
    p.add_argument("--hidden",               type=int,   default=64)
    p.add_argument("--latent",               type=int,   default=16)
    p.add_argument("--seq-len",              type=int,   default=60)
    p.add_argument("--batch",                type=int,   default=64)
    p.add_argument("--threshold-percentile", type=float, default=95.0)
    return p.parse_args()


def train():
    args = parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"device: {device}")

    os.makedirs("artifacts", exist_ok=True)

    # use pre-generated data if available, otherwise generate fresh
    normal_path = os.path.join("..", "data", "normal_sequences.npy")
    if os.path.exists(normal_path):
        print(f"loading pre-generated data from {normal_path}")
        normal_data = np.load(normal_path)
    else:
        print("generating training data...")
        normal_data = generate_normal(n_samples=5000, seq_len=args.seq_len)

    anomaly_data = generate_anomalous(n_samples=1000, seq_len=args.seq_len)
    normal_norm, stats = normalize(normal_data)
    anomaly_norm, _    = normalize(anomaly_data, stats=stats)

    with open("artifacts/norm_stats.json", "w") as f:
        json.dump({"min": stats["min"].tolist(), "max": stats["max"].tolist()}, f)

    tensor_data = torch.tensor(normal_norm)
    val_size    = int(0.1 * len(tensor_data))
    train_ds, val_ds = random_split(
        TensorDataset(tensor_data),
        [len(tensor_data) - val_size, val_size]
    )
    train_loader = DataLoader(train_ds, batch_size=args.batch, shuffle=True, num_workers=0)
    val_loader   = DataLoader(val_ds,   batch_size=args.batch, num_workers=0)

    model = LSTMAutoencoder(
        input_size=5,
        hidden_size=args.hidden,
        num_layers=2,
        latent_size=args.latent,
        seq_len=args.seq_len,
    ).to(device)

    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    criterion = nn.MSELoss()
    # patience=5 means we'll tolerate 5 epochs of no improvement before halving lr
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5, verbose=True)

    mlflow.set_experiment("neuralops-anomaly-detection")

    with mlflow.start_run(run_name=f"lstm-ae-h{args.hidden}-l{args.latent}"):
        mlflow.log_params({
            "epochs": args.epochs, "lr": args.lr, "hidden_size": args.hidden,
            "latent_size": args.latent, "seq_len": args.seq_len, "batch_size": args.batch,
            "threshold_percentile": args.threshold_percentile,
        })

        best_val_loss = float("inf")

        for epoch in range(1, args.epochs + 1):
            model.train()
            train_loss = 0.0
            for (batch,) in train_loader:
                batch = batch.to(device)
                optimizer.zero_grad()
                loss = criterion(model(batch), batch)
                loss.backward()
                # clip gradients — LSTMs can have exploding gradients without this
                nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                train_loss += loss.item()
            train_loss /= len(train_loader)

            model.eval()
            val_loss = 0.0
            with torch.no_grad():
                for (batch,) in val_loader:
                    batch = batch.to(device)
                    val_loss += criterion(model(batch), batch).item()
            val_loss /= len(val_loader)

            scheduler.step(val_loss)
            mlflow.log_metrics({"train_loss": train_loss, "val_loss": val_loss}, step=epoch)

            if epoch % 10 == 0:
                print(f"epoch {epoch:3d}/{args.epochs}  train={train_loss:.6f}  val={val_loss:.6f}")

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                torch.save(model.state_dict(), "artifacts/best_model.pt")

        # load best checkpoint before calibrating threshold
        model.load_state_dict(torch.load("artifacts/best_model.pt", map_location=device))
        model.eval()

        normal_errors  = model.reconstruction_error(torch.tensor(normal_norm).to(device)).cpu().numpy()
        anomaly_errors = model.reconstruction_error(torch.tensor(anomaly_norm).to(device)).cpu().numpy()

        threshold = float(np.percentile(normal_errors, args.threshold_percentile))
        print(f"\nthreshold (p{args.threshold_percentile:.0f}): {threshold:.6f}")

        tp = int((anomaly_errors > threshold).sum())
        fp = int((normal_errors  > threshold).sum())
        fn = int((anomaly_errors <= threshold).sum())
        precision = tp / (tp + fp + 1e-9)
        recall    = tp / (tp + fn + 1e-9)
        f1        = 2 * precision * recall / (precision + recall + 1e-9)

        print(f"precision={precision:.3f}  recall={recall:.3f}  f1={f1:.3f}")

        mlflow.log_metrics({
            "threshold": threshold, "precision": precision,
            "recall": recall, "f1_score": f1, "best_val_loss": best_val_loss,
        })

        with open("artifacts/threshold.json", "w") as f:
            json.dump({"threshold": threshold}, f)

        mlflow.log_artifacts("artifacts")
        mlflow.pytorch.log_model(
            model,
            artifact_path="model",
            registered_model_name="neuralops-lstm-autoencoder",
        )
        print("registered in MLflow model registry")


if __name__ == "__main__":
    train()
