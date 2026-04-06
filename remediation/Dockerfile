FROM python:3.10-slim
WORKDIR /app
COPY remediation/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY remediation/engine.py .

ENV KAFKA_BOOTSTRAP_SERVERS=localhost:9092
ENV KAFKA_ALERTS_TOPIC=anomaly-alerts
ENV K8S_NAMESPACE=neuralops
ENV AUDIT_LOG_PATH=/tmp/remediation_audit.jsonl
ENV KAFKA_SASL_USERNAME=""
ENV KAFKA_SASL_PASSWORD=""

CMD ["python", "engine.py"]
