# Local use — docker-compose builds this from the repo root
# so relative paths like ../ml/ work fine
FROM python:3.10-slim
WORKDIR /app

COPY drift/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY drift/drift_detector.py drift/retrain.py ./
COPY ml/model.py ml/data_generator.py ./

ENV PROMETHEUS_URL=http://prometheus:9090
ENV MLFLOW_TRACKING_URI=http://mlflow:5000
ENV REPORT_OUTPUT_DIR=/data/reports
ENV RETRAIN_SCRIPT=/app/retrain.py

CMD ["python", "drift_detector.py"]
