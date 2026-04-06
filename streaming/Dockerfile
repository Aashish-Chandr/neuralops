FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY metrics_exporter.py .

ENV PROMETHEUS_URL=http://prometheus.railway.internal:9090
ENV KAFKA_BOOTSTRAP_SERVERS=kafka.railway.internal:9092
ENV KAFKA_METRICS_TOPIC=metrics-stream
ENV SCRAPE_INTERVAL_SECONDS=15

CMD ["python", "metrics_exporter.py"]
