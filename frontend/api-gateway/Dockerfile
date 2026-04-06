FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .
ENV PROMETHEUS_URL=http://prometheus:9090
ENV INFERENCE_SERVER_URL=http://inference-server:8080
ENV MLFLOW_TRACKING_URI=http://mlflow:5000
EXPOSE 8090
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8090"]
