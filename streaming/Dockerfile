FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY metrics_exporter.py .
ENV PROMETHEUS_URL=http://prometheus:9090
ENV KAFKA_BOOTSTRAP_SERVERS=kafka:9092
CMD ["python", "metrics_exporter.py"]
