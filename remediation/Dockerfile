FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY engine.py .

ENV KAFKA_BOOTSTRAP_SERVERS=kafka.railway.internal:9092
ENV KAFKA_ALERTS_TOPIC=anomaly-alerts
ENV K8S_NAMESPACE=neuralops
ENV AUDIT_LOG_PATH=/data/remediation_audit.jsonl

CMD ["python", "engine.py"]
