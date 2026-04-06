FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY drift_detector.py retrain.py ./
# Copy ml module for retrain.py
COPY ../ml/model.py ../ml/data_generator.py ./
ENV PROMETHEUS_URL=http://prometheus:9090
ENV MLFLOW_TRACKING_URI=http://mlflow:5000
CMD ["python", "drift_detector.py"]
