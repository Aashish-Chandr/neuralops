FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .

ENV PROMETHEUS_URL=http://prometheus.railway.internal:9090
ENV INFERENCE_SERVER_URL=http://inference-server.railway.internal:8080
ENV MLFLOW_TRACKING_URI=http://mlflow.railway.internal:5000
ENV AUDIT_LOG_PATH=/data/remediation_audit.jsonl
ENV REPORT_OUTPUT_DIR=/data/reports
ENV CHAOS_STATE_PATH=/data/chaos_state.json

# Railway injects $PORT
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8090}"]
