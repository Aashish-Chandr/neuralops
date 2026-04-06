# NeuralOps

> AIOps platform that autonomously monitors microservices, detects anomalies with an LSTM Autoencoder, and self-heals infrastructure — no human required.

**GitHub:** https://github.com/Aashish-Chandr/neuralops

**Demo video:** _[Record and link here]_

```
Services → Prometheus → Kafka → LSTM Autoencoder → Anomaly Alert → Remediation Engine → K8s Action
                                        ↑
                              Evidently Drift Monitor
                                        ↓
                              Auto-Retrain Pipeline → MLflow Registry → ArgoCD Deploy
```

---

## Why I Built This

Modern systems run hundreds of microservices. When one fails, a DevOps engineer gets paged at 2 AM, logs in, investigates, and manually fixes it. This is reactive, slow, and doesn't scale. NeuralOps implements AIOps — the system watches itself, learns what "normal" looks like, detects deviations, and fixes them automatically. Every component in this project is something companies like Google, Netflix, and Datadog run in production.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         NeuralOps Pipeline                          │
│                                                                     │
│  ┌──────────┐   /metrics   ┌────────────┐   scrape   ┌──────────┐  │
│  │ 5x FastAPI│ ──────────► │ Prometheus │ ─────────► │  Kafka   │  │
│  │ Services  │             │            │  exporter  │  Stream  │  │
│  └──────────┘             └────────────┘            └────┬─────┘  │
│                                                           │         │
│                                                    metrics-stream   │
│                                                           │         │
│                                                    ┌──────▼──────┐  │
│                                                    │ LSTM        │  │
│                                                    │ Autoencoder │  │
│                                                    │ (PyTorch)   │  │
│                                                    └──────┬──────┘  │
│                                                           │         │
│                                                    anomaly-alerts   │
│                                                           │         │
│                                                    ┌──────▼──────┐  │
│                                                    │ Remediation │  │
│                                                    │ Engine      │  │
│                                                    └──────┬──────┘  │
│                                                           │         │
│                                              restart/scale/rollback │
│                                                           │         │
│                                                    ┌──────▼──────┐  │
│                                                    │ Kubernetes  │  │
│                                                    │ Cluster     │  │
│                                                    └─────────────┘  │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Evidently Drift Monitor (daily CronJob)                    │   │
│  │  training distribution vs production → retrain if drifted  │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack & Why

| Technology | Role | Why this over alternatives |
|---|---|---|
| FastAPI | Microservices | Async, auto-docs, Pydantic validation. Faster than Flask for I/O-bound services |
| Prometheus | Metrics collection | Pull-based scraping, native k8s integration, PromQL is powerful |
| Apache Kafka | Metrics streaming | Durable, replayable, decouples producers from consumers. SQS/RabbitMQ lack replay |
| PyTorch LSTM Autoencoder | Anomaly detection | Learns temporal patterns. Simple thresholds miss gradual degradation |
| MLflow | Experiment tracking + model registry | Open source, self-hostable, integrates with PyTorch natively |
| Evidently AI | Drift detection | Purpose-built for ML monitoring, statistical tests built in |
| Kubernetes | Orchestration | Industry standard, enables self-healing via pod restarts |
| Terraform | Infrastructure as Code | Declarative, state management, provider ecosystem |
| ArgoCD | GitOps deployment | Git as source of truth, automatic sync, audit trail |
| GitHub Actions | CI/CD | Native to GitHub, no separate server to maintain |
| Grafana | Observability | Best-in-class dashboarding for time-series data |

---

## Project Structure

```
neuralops/
├── frontend/               # React + TypeScript dashboard
│   ├── src/
│   │   ├── components/     # ServiceCard, LiveChart, AnomalyScorePanel, etc.
│   │   ├── App.tsx         # Main app with 4 tabs
│   │   ├── api.ts          # API client (auto-falls back to mock data)
│   │   ├── mockData.ts     # Demo data for offline use
│   │   └── types.ts        # Shared TypeScript types
│   ├── api-gateway/        # FastAPI backend the frontend talks to
│   │   └── main.py         # Aggregates Prometheus, MLflow, audit logs
│   ├── Dockerfile          # Multi-stage: build → nginx
│   └── nginx.conf
├── services/               # 5x FastAPI microservices + shared base
│   ├── base_service.py     # Shared Prometheus metrics + chaos mode
│   ├── user-service/
│   ├── order-service/
│   ├── payment-service/    # Intentionally higher latency
│   ├── inventory-service/
│   ├── notification-service/
│   ├── requirements.txt
│   ├── Dockerfile.template
│   └── docker-compose.yml
├── ml/
│   ├── model.py            # LSTM Autoencoder (PyTorch)
│   ├── data_generator.py   # Synthetic training data
│   ├── train.py            # Training + MLflow logging
│   ├── inference_server.py # FastAPI prediction endpoint
│   ├── kafka_consumer.py   # Reads metrics-stream, publishes alerts
│   ├── supervisord.conf
│   └── Dockerfile
├── streaming/
│   ├── metrics_exporter.py # Prometheus → Kafka bridge
│   ├── consumer_debug.py   # Debug: print all Kafka messages
│   └── Dockerfile
├── remediation/
│   ├── engine.py           # Rule-based K8s auto-remediation
│   └── Dockerfile
├── drift/
│   ├── drift_detector.py   # Evidently drift reports + retrain trigger
│   ├── retrain.py          # Automated retraining pipeline
│   └── Dockerfile
├── infra/
│   ├── terraform/          # EKS, VPC, S3, Kafka, Prometheus, ArgoCD
│   ├── helm/neuralops/     # Helm chart for all components
│   └── argocd/             # ArgoCD Application manifests
├── monitoring/
│   ├── prometheus/prometheus.yml
│   └── grafana/dashboards/neuralops-overview.json
├── .github/workflows/
│   ├── ci.yml              # PR: lint + test + build
│   └── cd.yml              # main: build + push + update helm values
└── docker-compose.full.yml # Full local stack
```

---

## Quick Start (Local)

### Prerequisites
- Docker Desktop
- Python 3.10+
- Node.js 20+
- `kubectl` + Minikube (for K8s features)

### 1. Run the full stack

```bash
cd neuralops
docker-compose -f docker-compose.full.yml up --build
```

Services available:
- Frontend Dashboard:    http://localhost:3001
- API Gateway:          http://localhost:8090/docs
- User Service:         http://localhost:8001/docs
- Order Service:        http://localhost:8002/docs
- Payment Service:      http://localhost:8003/docs
- Inventory Service:    http://localhost:8004/docs
- Notification Service: http://localhost:8005/docs
- Prometheus:           http://localhost:9090
- Grafana:              http://localhost:3000  (admin / neuralops-admin)
- MLflow:               http://localhost:5000
- Inference Server:     http://localhost:8080/docs

### 2. Frontend dev mode (hot reload)

```bash
cd frontend
npm install
npm run dev   # http://localhost:3001
```

The frontend works in demo mode (mock data) when the backend isn't running.
When the backend is up, it automatically switches to live data.

### 2. Train the model

```bash
cd ml
pip install -r requirements.txt
python train.py --epochs 50 --hidden 64 --latent 16
```

### 3. Trigger chaos mode (demo)

```bash
# Enable chaos on payment service
CHAOS_PAYMENT=true docker-compose -f docker-compose.full.yml up payment-service
```

Watch the Grafana dashboard — anomaly scores will rise and the remediation engine will act.

### 4. Verify the Kafka pipeline

```bash
cd streaming
pip install -r requirements.txt
python consumer_debug.py
```

---

## Kubernetes Deployment

### Local (Minikube)

```bash
minikube start --memory=8192 --cpus=4

# Install ArgoCD
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Deploy NeuralOps via Helm
helm install neuralops infra/helm/neuralops/ -n neuralops --create-namespace

# Apply ArgoCD app (GitOps from here on)
kubectl apply -f infra/argocd/app-neuralops.yaml
```

### Cloud (AWS EKS)

```bash
cd infra/terraform
terraform init
terraform plan -var="environment=prod"
terraform apply
```

---

## ML Model Details

**Architecture:** LSTM Autoencoder
- Input: `(batch, 60, 5)` — 60 timesteps × 5 features
- Features: `[cpu%, memory%, latency_p99_ms, error_rate%, rps]`
- Encoder: 2-layer LSTM → linear projection → 16-dim latent vector
- Decoder: latent → repeat → 2-layer LSTM → linear projection → reconstruction
- Loss: MSE reconstruction error

**Anomaly detection:** Train only on normal data. At inference, reconstruction error > threshold (95th percentile of training errors) = anomaly.

**MLflow tracking:** Every run logs hyperparameters, train/val loss curves, threshold, precision/recall/F1, and the model artifact. Best model is registered in the Model Registry under `neuralops-lstm-autoencoder`.

---

## Remediation Rules

| Pattern | Action |
|---|---|
| High error rate + low RPS | Restart pod (suspected crash) |
| High CPU + high memory + high latency | Scale up replicas (suspected overload) |
| High errors + normal latency | Rollback deployment (suspected bad deploy) |

After every action, the engine waits 5 minutes and verifies recovery. If the service is still unhealthy, it escalates via Slack webhook.

---

## Model Drift Detection

Runs daily via Kubernetes CronJob. Uses Evidently AI to compare:
- Training data distribution vs last 24h of production metrics
- If >30% of features show statistical drift → triggers retraining pipeline
- New model is only promoted to Production if F1 score improves

---

## CI/CD Flow

```
PR opened → lint (flake8) + tests + docker build (no push)
         ↓
Merged to main → build + push images to GHCR with commit SHA tag
              → update image tags in helm/values.yaml
              → ArgoCD detects values.yaml change → auto-deploys
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `CHAOS_MODE` | `false` | Enable chaos mode in microservices |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Kafka broker address |
| `PROMETHEUS_URL` | `http://localhost:9090` | Prometheus API URL |
| `MLFLOW_TRACKING_URI` | `http://localhost:5000` | MLflow server URL |
| `DRIFT_THRESHOLD` | `0.3` | Fraction of drifted features to trigger retrain |
| `VERIFY_WAIT_SECONDS` | `300` | Seconds to wait before verifying remediation |
| `SLACK_WEBHOOK_URL` | `` | Slack webhook for escalation alerts |
