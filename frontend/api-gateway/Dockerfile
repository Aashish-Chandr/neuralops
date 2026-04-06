FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .

# Render and Railway both inject $PORT at runtime
# Defaults make local docker-compose work without changes
ENV PROMETHEUS_URL=""
ENV MLFLOW_TRACKING_URI=""
ENV AUDIT_LOG_PATH=/tmp/remediation_audit.jsonl
ENV REPORT_OUTPUT_DIR=/tmp/reports
ENV CHAOS_STATE_PATH=/tmp/chaos_state.json

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8090}"]
