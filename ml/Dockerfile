FROM python:3.10-slim
WORKDIR /app

COPY ml/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt supervisor

COPY ml/model.py ml/inference_server.py ml/kafka_consumer.py ml/supervisord.conf ./

# artifacts/ (threshold.json, norm_stats.json, best_model.pt) are optional at build time.
# If missing, the inference server falls back to defaults on startup.
# In production, mount them as a volume or bake them in after training.
COPY ml/artifacts/ ./artifacts/

ENV MLFLOW_TRACKING_URI=""
ENV KAFKA_BOOTSTRAP_SERVERS="localhost:9092"
ENV KAFKA_SASL_USERNAME=""
ENV KAFKA_SASL_PASSWORD=""
ENV MODEL_NAME=neuralops-lstm-autoencoder
ENV MODEL_STAGE=Production

COPY ml/supervisord.conf /etc/supervisord.conf

CMD ["supervisord", "-c", "/etc/supervisord.conf"]
