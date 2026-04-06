"""
Inference server. Loads the production model from MLflow on startup,
serves predictions via /predict, exposes Prometheus metrics.

A few things worth knowing:
- If MLflow is unreachable at startup (common during first deploy), it falls back
  to artifacts/best_model.pt. This means the service starts even if MLflow is down.
- The threshold is loaded from artifacts/threshold.json. If that file doesn't exist
  (e.g. you haven't trained yet), it defaults to 0.05 which is a reasonable starting point.
- /reload-model lets you hot-swap the model without restarting the container.
  The drift detector calls this after promoting a new version.
"""
import os
import json
import logging
import numpy as np
import torch
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel
from prometheus_client import Gauge, Counter, generate_latest, CONTENT_TYPE_LATEST
import mlflow.pytorch

log = logging.getLogger("inference-server")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
MODEL_NAME          = os.getenv("MODEL_NAME",  "neuralops-lstm-autoencoder")
MODEL_STAGE         = os.getenv("MODEL_STAGE", "Production")
THRESHOLD_PATH      = os.getenv("THRESHOLD_PATH",   "artifacts/threshold.json")
NORM_STATS_PATH     = os.getenv("NORM_STATS_PATH",  "artifacts/norm_stats.json")

app = FastAPI(title="NeuralOps Inference Server", docs_url="/docs")

ANOMALY_SCORE   = Gauge("anomaly_score",          "Reconstruction error per service", ["service"])
ANOMALY_COUNTER = Counter("anomalies_detected_total", "Anomalies detected",           ["service"])
PREDICT_COUNTER = Counter("predictions_total",    "Total predictions served")

# module-level state — reloaded by /reload-model
model      = None
threshold  = 0.05
norm_stats = None
device     = torch.device("cpu")


def load_model():
    global model, threshold, norm_stats

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    try:
        uri = f"models:/{MODEL_NAME}/{MODEL_STAGE}"
        log.info(f"loading model from {uri}")
        model = mlflow.pytorch.load_model(uri, map_location=device)
        model.eval()
        log.info("model loaded from registry")
    except Exception as e:
        log.warning(f"MLflow unavailable ({e}), falling back to local checkpoint")
        from model import LSTMAutoencoder
        model = LSTMAutoencoder()
        ckpt = "artifacts/best_model.pt"
        if os.path.exists(ckpt):
            model.load_state_dict(torch.load(ckpt, map_location=device))
            log.info(f"loaded from {ckpt}")
        else:
            log.warning("no checkpoint found — using untrained model, predictions will be meaningless")
        model.eval()

    if os.path.exists(THRESHOLD_PATH):
        with open(THRESHOLD_PATH) as f:
            threshold = json.load(f)["threshold"]
        log.info(f"threshold: {threshold:.6f}")
    else:
        log.warning(f"threshold file not found at {THRESHOLD_PATH}, using default {threshold}")

    if os.path.exists(NORM_STATS_PATH):
        with open(NORM_STATS_PATH) as f:
            raw = json.load(f)
        norm_stats = {"min": np.array(raw["min"]), "max": np.array(raw["max"])}
    else:
        log.warning("norm_stats.json not found — inputs will not be normalized")


@app.on_event("startup")
def startup():
    load_model()


class MetricSequence(BaseModel):
    service: str
    sequence: list[list[float]]  # (60, 5): [cpu%, mem%, latency_ms, error_rate%, rps]


class PredictionResponse(BaseModel):
    service: str
    anomaly_score: float
    is_anomaly: bool
    threshold: float
    top_features: dict[str, float]


@app.post("/predict", response_model=PredictionResponse)
def predict(req: MetricSequence):
    if model is None:
        raise HTTPException(503, "model not loaded")

    seq = np.array(req.sequence, dtype=np.float32)
    if seq.shape != (60, 5):
        raise HTTPException(422, f"expected shape (60, 5), got {seq.shape}")

    if norm_stats is not None:
        denom = norm_stats["max"] - norm_stats["min"]
        denom[denom == 0] = 1.0
        seq = (seq - norm_stats["min"]) / denom

    tensor = torch.tensor(seq).unsqueeze(0)
    score  = float(model.reconstruction_error(tensor).item())

    PREDICT_COUNTER.inc()
    ANOMALY_SCORE.labels(service=req.service).set(score)

    is_anomaly = score > threshold
    if is_anomaly:
        ANOMALY_COUNTER.labels(service=req.service).inc()

    # per-feature contribution to reconstruction error
    with torch.no_grad():
        recon = model(tensor).squeeze(0).numpy()
    feature_errors = np.mean((seq - recon) ** 2, axis=0)
    feature_names  = ["cpu_usage_percent", "memory_usage_percent", "latency_ms", "error_rate_percent", "rps"]

    return PredictionResponse(
        service=req.service,
        anomaly_score=score,
        is_anomaly=is_anomaly,
        threshold=threshold,
        top_features=dict(zip(feature_names, feature_errors.tolist())),
    )


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": model is not None, "threshold": threshold}


@app.post("/reload-model")
def reload_model():
    """Hot-reload the model from MLflow. Called by the drift detector after promoting a new version."""
    load_model()
    return {"status": "reloaded", "threshold": threshold}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
