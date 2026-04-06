<div align="center">
 
<img src="https://img.shields.io/badge/NeuralOps-AIOps%20Platform-6366f1?style=for-the-badge&logo=kubernetes&logoColor=white" alt="NeuralOps" height="40"/>
 
# NeuralOps
 
**Autonomous AIOps platform that monitors microservices, detects anomalies with deep learning, and self-heals infrastructure — without human intervention.**
 
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PyTorch](https://img.shields.io/badge/PyTorch-LSTM%20Autoencoder-EE4C2C?style=flat-square&logo=pytorch&logoColor=white)](https://pytorch.org)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-Self--Healing-326CE5?style=flat-square&logo=kubernetes&logoColor=white)](https://kubernetes.io)
[![Kafka](https://img.shields.io/badge/Apache%20Kafka-Streaming-231F20?style=flat-square&logo=apachekafka&logoColor=white)](https://kafka.apache.org)
[![Terraform](https://img.shields.io/badge/Terraform-IaC-7B42BC?style=flat-square&logo=terraform&logoColor=white)](https://terraform.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)
 
[Overview](#-overview) · [Architecture](#-architecture) · [Tech Stack](#-tech-stack) · [Quick Start](#-quick-start) · [ML Model](#-ml-model) · [Kubernetes](#-kubernetes-deployment) · [CI/CD](#-cicd-pipeline)
 
</div>
 
---
 
## 📌 Overview
 
Modern distributed systems run hundreds of microservices. When one degrades, a DevOps engineer gets paged at 2 AM, manually investigates logs, and applies a fix. This is reactive, slow, and doesn't scale.
 
**NeuralOps** implements the full AIOps lifecycle:
 
| Stage | What Happens |
|---|---|
| 🔭 **Observe** | 5 FastAPI microservices emit Prometheus metrics |
| 🌊 **Stream** | Prometheus → Kafka bridge delivers a real-time metrics stream |
| 🧠 **Detect** | An LSTM Autoencoder learns normal behaviour and flags deviations |
| 🔔 **Alert** | Anomaly scores are published to a Kafka topic and the dashboard |
| 🔧 **Remediate** | A rule-based engine restarts, scales, or rolls back affected pods |
| 📊 **Track** | MLflow logs every experiment; Grafana visualises everything |
| 🔄 **Adapt** | Evidently AI detects data drift daily and triggers auto-retraining |
 
> Every component in this project mirrors what Google, Netflix, and Datadog run at scale.
 
---
 
## 🏗 Architecture
 
```
┌──────────────────────────────────────────────────────────────────────┐
│                          NeuralOps Pipeline                          │
│                                                                      │
│  ┌──────────────┐  /metrics  ┌────────────┐  exporter  ┌─────────┐  │
│  │  5× FastAPI  │──────────▶│ Prometheus │───────────▶│  Kafka  │  │
│  │  Microsvcs   │           └────────────┘            │ Stream  │  │
│  └──────────────┘                                     └────┬────┘  │
│                                                            │        │
│                                                     metrics-stream  │
│                                                            │        │
│                                                    ┌───────▼──────┐ │
│                                                    │     LSTM     │ │
│                                                    │ Autoencoder  │ │
│                                                    │  (PyTorch)   │ │
│                                                    └───────┬──────┘ │
│                                                            │        │
│                                                     anomaly-alerts  │
│                                                            │        │
│                                                    ┌───────▼──────┐ │
│                                                    │ Remediation  │ │
│                                                    │   Engine     │ │
│                                                    └───────┬──────┘ │
│                                                            │        │
│                                           restart / scale / rollback│
│                                                            │        │
│                                                    ┌───────▼──────┐ │
│                                                    │  Kubernetes  │ │
│                                                    │   Cluster    │ │
│                                                    └──────────────┘ │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Evidently Drift Monitor  (daily CronJob)                    │   │
│  │  training dist. vs production → auto-retrain if drifted      │   │
│  │  new model promoted only if F1 improves → ArgoCD deploys     │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```
 
---
 
## 🛠 Tech Stack
 
| Technology | Role | Design Rationale |
|---|---|---|
| **FastAPI** | Microservices | Async-first, auto-generated OpenAPI docs, Pydantic validation — faster than Flask for I/O-bound services |
| **Prometheus** | Metrics collection | Pull-based scraping, native Kubernetes integration, powerful PromQL |
| **Apache Kafka** | Metrics streaming | Durable, replayable event log — decouples producers from consumers in a way SQS/RabbitMQ cannot |
| **PyTorch LSTM Autoencoder** | Anomaly detection | Learns temporal patterns across sliding windows; simple static thresholds miss gradual degradation |
| **MLflow** | Experiment tracking & model registry | Open-source, self-hostable, integrates natively with PyTorch |
| **Evidently AI** | Data drift detection | Purpose-built for ML monitoring with built-in statistical tests |
| **Kubernetes** | Orchestration | Industry standard; enables self-healing via native pod restart and HPA |
| **Terraform** | Infrastructure as Code | Declarative, state-managed provisioning with a rich provider ecosystem |
| **ArgoCD** | GitOps deployments | Git as the single source of truth, automatic sync, full audit trail |
| **GitHub Actions** | CI/CD | Native to GitHub — no separate server to maintain |
| **Grafana** | Observability dashboards | Best-in-class time-series visualisation |
 
**Languages:** Python 60.7% · TypeScript 20.2% · HCL 7.6% · JavaScript 4.2% · Makefile 2.8% · CSS 2.3%
 
---
 
## 📁 Project Structure
 
```
neuralops/
├── frontend/                     # React + TypeScript observability dashboard
│   ├── src/
│   │   ├── components/           # ServiceCard, LiveChart, AnomalyScorePanel, …
│   │   ├── App.tsx               # Main app — 4 tabs
│   │   ├── api.ts                # API client (auto-falls back to mock data)
│   │   ├── mockData.ts           # Offline demo data
│   │   └── types.ts              # Shared TypeScript types
│   ├── api-gateway/
│   │   └── main.py               # FastAPI gateway — aggregates Prometheus, MLflow, audit logs
│   ├── Dockerfile                # Multi-stage: build → nginx
│   └── nginx.conf
│
├── services/                     # 5× FastAPI microservices + shared base
│   ├── base_service.py           # Shared Prometheus metrics + chaos mode
│   ├── user-service/
│   ├── order-service/
│   ├── payment-service/          # Intentionally higher latency (chaos demo)
│   ├── inventory-service/
│   ├── notification-service/
│   └── Dockerfile.template
│
├── ml/
│   ├── model.py                  # LSTM Autoencoder (PyTorch)
│   ├── data_generator.py         # Synthetic training data
│   ├── train.py                  # Training loop + MLflow experiment logging
│   ├── inference_server.py       # FastAPI /predict endpoint
│   └── kafka_consumer.py         # Reads metrics-stream, publishes anomaly alerts
│
├── streaming/
│   ├── metrics_exporter.py       # Prometheus → Kafka bridge
│   └── consumer_debug.py         # Debug: print all Kafka messages
│
├── remediation/
│   └── engine.py                 # Rule-based Kubernetes auto-remediation
│
├── drift/
│   ├── drift_detector.py         # Evidently drift reports + retrain trigger
│   └── retrain.py                # Automated retraining pipeline
│
├── infra/
│   ├── terraform/                # EKS, VPC, S3, Kafka, Prometheus, ArgoCD
│   ├── helm/neuralops/           # Helm chart for all components
│   └── argocd/                   # ArgoCD Application manifests
│
├── monitoring/
│   ├── prometheus/prometheus.yml
│   └── grafana/dashboards/neuralops-overview.json
│
├── .github/workflows/
│   ├── ci.yml                    # PR: lint + test + build
│   └── cd.yml                    # main: build → push → update Helm values
│
├── docker-compose.full.yml       # Full local stack
├── Makefile                      # Convenience targets
└── .env.example
```
 
---
 
## ⚡ Quick Start
 
### Prerequisites
 
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) ≥ 4.x
- Python 3.10+
- Node.js 20+
- `kubectl` + [Minikube](https://minikube.sigs.k8s.io/) _(for Kubernetes features)_
 
---
 
### 1 · Start the full stack
 
```bash
git clone https://github.com/Aashish-Chandr/neuralops.git
cd neuralops
cp .env.example .env          # edit as needed
docker-compose -f docker-compose.full.yml up --build
```
 
Once running, the following endpoints are available:
 
| Service | URL |
|---|---|
| 🖥 Frontend Dashboard | http://localhost:3001 |
| 🔀 API Gateway (docs) | http://localhost:8090/docs |
| 👤 User Service | http://localhost:8001/docs |
| 📦 Order Service | http://localhost:8002/docs |
| 💳 Payment Service | http://localhost:8003/docs |
| 🗄 Inventory Service | http://localhost:8004/docs |
| 🔔 Notification Service | http://localhost:8005/docs |
| 📈 Prometheus | http://localhost:9090 |
| 📊 Grafana | http://localhost:3000 _(admin / neuralops-admin)_ |
| 🧪 MLflow | http://localhost:5000 |
| 🤖 Inference Server | http://localhost:8080/docs |
 
---
 
### 2 · Frontend dev mode (hot reload)
 
```bash
cd frontend
npm install
npm run dev        # http://localhost:3001
```
 
> The dashboard operates in **demo mode** (mock data) when the backend is offline and automatically switches to live data when services are up.
 
---
 
### 3 · Train the anomaly detection model
 
```bash
cd ml
pip install -r requirements.txt
python train.py --epochs 50 --hidden 64 --latent 16
```
 
Results are logged to MLflow at http://localhost:5000.
 
---
 
### 4 · Trigger chaos mode
 
```bash
# Inject chaos into the payment service
CHAOS_PAYMENT=true docker-compose -f docker-compose.full.yml up payment-service
```
 
Watch the Grafana dashboard — anomaly scores will climb and the remediation engine will respond automatically.
 
---
 
### 5 · Inspect the Kafka pipeline
 
```bash
cd streaming
pip install -r requirements.txt
python consumer_debug.py      # prints all messages from metrics-stream
```
 
---
 
## 🧠 ML Model
 
### LSTM Autoencoder
 
The model is trained **only on normal operating data**. At inference, a high reconstruction error signals an anomaly.
 
```
Input  →  (batch, 60, 5)        60-step sliding window × 5 features
                                 [cpu%, memory%, latency_p99_ms, error_rate%, rps]
         │
         ▼
Encoder  →  2-layer LSTM  →  Linear projection  →  16-dim latent vector
         │
         ▼
Decoder  →  Repeat latent  →  2-layer LSTM  →  Linear projection  →  Reconstruction
         │
         ▼
Loss     →  MSE reconstruction error
```
 
**Anomaly threshold:** 95th percentile of reconstruction errors observed on the training set. Anything above this at inference time is flagged as anomalous.
 
**MLflow tracking:** Every training run logs hyperparameters, train/val loss curves, the computed threshold, and precision/recall/F1 scores. The best model is registered under `neuralops-lstm-autoencoder` in the Model Registry.
 
---
 
## 🔧 Remediation Engine
 
When an anomaly alert lands, the engine applies a rule-based decision tree and acts on Kubernetes:
 
| Observed Pattern | Automated Action |
|---|---|
| High error rate + low RPS | **Restart pod** — suspected crash loop |
| High CPU + high memory + high latency | **Scale up replicas** — suspected overload |
| High errors + normal latency | **Rollback deployment** — suspected bad release |
 
After each action the engine waits **5 minutes**, re-evaluates service health, and if the issue persists it escalates via **Slack webhook**.
 
---
 
## 📉 Drift Detection & Auto-Retraining
 
A Kubernetes **CronJob** runs Evidently AI daily:
 
1. Compares the training-time feature distribution against the last 24 h of production metrics.
2. If **> 30 %** of features show statistically significant drift, the retraining pipeline is triggered.
3. The newly trained model is promoted to `Production` in the MLflow registry **only if its F1 score improves** over the current champion.
4. ArgoCD detects the updated model reference in `helm/values.yaml` and deploys automatically.
 
---
 
## ☸️ Kubernetes Deployment
 
### Local — Minikube
 
```bash
minikube start --memory=8192 --cpus=4
 
# Install ArgoCD
kubectl create namespace argocd
kubectl apply -n argocd \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
 
# Deploy NeuralOps
helm install neuralops infra/helm/neuralops/ \
  -n neuralops --create-namespace
 
# Hand off to GitOps
kubectl apply -f infra/argocd/app-neuralops.yaml
```
 
### Cloud — AWS EKS
 
```bash
cd infra/terraform
terraform init
terraform plan  -var="environment=prod"
terraform apply
```
 
Terraform provisions: **EKS cluster · VPC · S3 (artifact storage) · MSK (Kafka) · Prometheus · ArgoCD**.
 
---
 
## 🔄 CI/CD Pipeline
 
```
Pull Request opened
  └─▶  flake8 lint  →  pytest  →  docker build (no push)
 
Merge to main
  └─▶  Build & push images to GHCR  (tagged with commit SHA)
         └─▶  Update image tags in helm/values.yaml
                └─▶  ArgoCD detects diff  →  auto-deploys to cluster
```
 
---
 
## ⚙️ Environment Variables
 
| Variable | Default | Description |
|---|---|---|
| `CHAOS_MODE` | `false` | Enable fault injection in microservices |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Kafka broker address |
| `PROMETHEUS_URL` | `http://localhost:9090` | Prometheus API base URL |
| `MLFLOW_TRACKING_URI` | `http://localhost:5000` | MLflow tracking server URL |
| `DRIFT_THRESHOLD` | `0.3` | Fraction of drifted features required to trigger retraining |
| `VERIFY_WAIT_SECONDS` | `300` | Seconds to wait before verifying post-remediation health |
| `SLACK_WEBHOOK_URL` | _(empty)_ | Slack incoming webhook URL for escalation alerts |
 
Copy `.env.example` to `.env` and override as needed before starting the stack.
 
---
 
## 🗺 Roadmap
 
- [ ] Add LLM-assisted root-cause explanation surfaced in the dashboard
- [ ] Extend LSTM model to multivariate cross-service correlations
- [ ] Support GKE and AKS alongside EKS in Terraform
- [ ] Prometheus Alertmanager integration as a secondary alert channel
- [ ] Demo video walkthrough
 
---
 
## 🤝 Contributing
 
Contributions, issues, and feature requests are welcome!
 
```bash
# Fork the repo, then:
git checkout -b feature/my-feature
git commit -m "feat: add my feature"
git push origin feature/my-feature
# Open a Pull Request
```
 
Please ensure `flake8` passes and relevant tests are added before opening a PR.
 
---
 
## 📄 License
 
Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for details.
 
---
 
<div align="center">
 
Built by [Aashish Chandr](https://github.com/Aashish-Chandr) · Give it a ⭐ if you found it useful!
 
</div>
