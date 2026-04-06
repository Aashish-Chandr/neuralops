FROM python:3.10-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY model.py inference_server.py kafka_consumer.py ./
COPY artifacts/ ./artifacts/

ENV MLFLOW_TRACKING_URI=http://mlflow:5000
ENV KAFKA_BOOTSTRAP_SERVERS=kafka:9092
ENV INFERENCE_SERVER_URL=http://localhost:8080

# Start both inference server and kafka consumer via supervisord
RUN pip install supervisor
COPY supervisord.conf /etc/supervisord.conf

EXPOSE 8080
CMD ["supervisord", "-c", "/etc/supervisord.conf"]
