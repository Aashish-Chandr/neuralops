FROM python:3.10-slim
WORKDIR /app
COPY streaming/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY streaming/metrics_exporter.py .

ENV PROMETHEUS_URL=http://prometheus:9090
ENV KAFKA_BOOTSTRAP_SERVERS=localhost:9092
ENV KAFKA_METRICS_TOPIC=metrics-stream
ENV SCRAPE_INTERVAL_SECONDS=15
ENV KAFKA_SASL_USERNAME=""
ENV KAFKA_SASL_PASSWORD=""

CMD ["python", "metrics_exporter.py"]
