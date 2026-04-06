"""
NeuralOps Inference Server
Loads the production LSTM Autoencoder from MLflow and serves predictions.
"""
import os
import json
import logging
import numpy as np
import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from prometheus_client import Gauge, Counter, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
import mlflow.pytorch

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("inference-server")

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
MODEL_NAME          = os.getenv("MODEL_NAME", "neuralops-lstm-autoencoder")
MODEL_STAGE         = os.getenv("MODEL_STAGE", "Production")
THRESHOLD_PATH      = os.getenv("THRESHOLD_PATH", "artifacts/threshold.json")
NORM_STATS_PATH     = os.getenv("NORM_STATS_PATH", "artifacts/norm_stats.json")

app = FastAPI(title="NeuralOps Inference Server")

# Prometheus metrics
ANOMALY_SCORE   = Gauge("anomaly_score",   "Current anomaly reconstruction error", ["service"])
ANOMALY_COUNTER = Counter("anomalies_detected_total", "Total anomalies detected",  ["service"])
PREDICT_COUNTER = Counter("predictions_total", "Total predictions made")

model = None
threshold = 0.05
norm_stats = None
device = torch.device("cpu")


def load_model():
    global model, threshold, norm_stats
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    try:
        model_uri = f"models:/{MODEL_NAME}/{MODEL_STAGE}"
        log.info(f"Loading model from {model_uri}")
        model = mlflow.pytorch.load_model(model_uri, map_location=device)
        model.eval()
        log.info("Model loaded from MLflow registry")
    except Exception as e:
        log.warning(f"MLflow load failed ({e}), loading from local artifacts/best_model.pt")
        from model import LSTMAutoencoder
        model = LSTMAutoencoder()
        if os.path.exists("artifacts/best_model.pt"):
            model.load_state_dict(torch.load("artifacts/best_model.pt", map_location=device))
        model.eval()

    if os.path.exists(THRESHOLD_PATH):
        with open(THRESHOLD_PATH) as f:
            threshold = json.load(f)["threshold"]
        log.info(f"Threshold loaded: {threshold:.6f}")

    if os.path.exists(NORM_STATS_PATH):
        with open(NORM_STATS_PATH) as f:
            raw = json.load(f)
            norm_stats = {"min": np.array(raw["min"]), "max": np.array(raw["max"])}
        log.info("Normalization stats loaded")


@app.on_event("startup")
def startup():
    load_model()


class MetricSequence(BaseModel):
    service: str
    # List of 60 timesteps, each with 5 features:
    # [cpu_usage_percent, memory_usage_percent, latency_ms, error_rate_percent, rps]
    sequence: list[list[float]]


class PredictionResponse(BaseModel):
    service: str
    anomaly_score: float
    is_anomaly: bool
    threshold: float
    top_features: dict


@app.post("/predict", response_model=PredictionResponse)
def predict(req: MetricSequence):
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    seq = np.array(req.sequence, dtype=np.float32)
    if seq.shape != (60, 5):
        raise HTTPException(status_code=422, detail=f"Expected shape (60,5), got {seq.shape}")

    # Normalize
    if norm_stats is not None:
        denom = norm_stats["max"] - norm_stats["min"]
        denom[denom == 0] = 1.0
        seq = (seq - norm_stats["min"]) / denom

    tensor = torch.tensor(seq).unsqueeze(0)  # (1, 60, 5)
    score = float(model.reconstruction_error(tensor).item())

    PREDICT_COUNTER.inc()
    ANOMALY_SCORE.labels(service=req.service).set(score)

    is_anomaly = score > threshold
    if is_anomaly:
        ANOMALY_COUNTER.labels(service=req.service).inc()

    # Identify which features contributed most to the error
    with torch.no_grad():
        recon = model(tensor).squeeze(0).numpy()
    orig = seq if norm_stats is None else seq
    feature_errors = np.mean((orig - recon) ** 2, axis=0)
    feature_names = ["cpu_usage_percent", "memory_usage_percent", "latency_ms", "error_rate_percent", "rps"]
    top_features = dict(zip(feature_names, feature_errors.tolist()))

    return PredictionResponse(
        service=req.service,
        anomaly_score=score,
        is_anomaly=is_anomaly,
        threshold=threshold,
        top_features=top_features,
    )


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": model is not None, "threshold": threshold}


@app.post("/reload-model")
def reload_model():
    load_model()
    return {"status": "reloaded"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
