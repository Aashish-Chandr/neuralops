FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY engine.py .
ENV KAFKA_BOOTSTRAP_SERVERS=kafka:9092
ENV K8S_NAMESPACE=neuralops
CMD ["python", "engine.py"]
