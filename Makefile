.PHONY: help dev down build train test lint data chaos-on chaos-off logs clean

# Default target
help:
	@echo ""
	@echo "  NeuralOps — Available Commands"
	@echo "  ─────────────────────────────────────────────────────"
	@echo "  make dev          Start full local stack"
	@echo "  make down         Stop all containers"
	@echo "  make build        Build all Docker images"
	@echo "  make data         Generate training data"
	@echo "  make train        Train the LSTM Autoencoder"
	@echo "  make test         Run all tests"
	@echo "  make lint         Lint all Python code"
	@echo "  make chaos-on     Enable chaos on payment-service"
	@echo "  make chaos-off    Disable chaos on payment-service"
	@echo "  make logs         Tail all container logs"
	@echo "  make clean        Remove containers, volumes, data"
	@echo ""

# ── Stack ─────────────────────────────────────────────────────────────────────
dev:
	docker-compose -f docker-compose.full.yml up --build

dev-detached:
	docker-compose -f docker-compose.full.yml up --build -d
	@echo ""
	@echo "  Stack running:"
	@echo "  Frontend:   http://localhost:3001"
	@echo "  Grafana:    http://localhost:3000  (admin / neuralops-admin)"
	@echo "  Prometheus: http://localhost:9090"
	@echo "  MLflow:     http://localhost:5000"
	@echo "  API Docs:   http://localhost:8080/docs"
	@echo ""

down:
	docker-compose -f docker-compose.full.yml down

down-volumes:
	docker-compose -f docker-compose.full.yml down -v

build:
	docker-compose -f docker-compose.full.yml build

logs:
	docker-compose -f docker-compose.full.yml logs -f

# ── ML ────────────────────────────────────────────────────────────────────────
data:
	python scripts/generate_training_data.py

train:
	cd ml && python train.py --epochs 50 --hidden 64 --latent 16

train-quick:
	cd ml && python train.py --epochs 10 --hidden 32 --latent 8

# ── Testing ───────────────────────────────────────────────────────────────────
test:
	python -m pytest ml/tests/ remediation/tests/ tests/ -v

test-unit:
	python -m pytest ml/tests/ remediation/tests/ -v

test-integration:
	python -m pytest tests/integration/ -v

test-e2e:
	python -m pytest tests/e2e/ -v

test-frontend:
	cd frontend && npm run type-check

lint:
	flake8 ml/ streaming/ remediation/ drift/ services/ \
		--max-line-length=120 \
		--exclude=__pycache__,.venv \
		--ignore=E501,W503

# ── Chaos ─────────────────────────────────────────────────────────────────────
chaos-on:
	@echo "Enabling chaos on payment-service..."
	CHAOS_PAYMENT=true docker-compose -f docker-compose.full.yml up -d payment-service
	@echo "Chaos enabled. Watch http://localhost:3001"

chaos-off:
	@echo "Disabling chaos on payment-service..."
	CHAOS_PAYMENT=false docker-compose -f docker-compose.full.yml up -d payment-service
	@echo "Chaos disabled."

# ── Kafka ─────────────────────────────────────────────────────────────────────
kafka-topics:
	docker-compose -f docker-compose.full.yml exec kafka \
		kafka-topics --list --bootstrap-server localhost:9092

kafka-tail:
	cd streaming && python consumer_debug.py

# ── Cleanup ───────────────────────────────────────────────────────────────────
clean:
	docker-compose -f docker-compose.full.yml down -v --remove-orphans
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf ml/artifacts ml/.pytest_cache remediation/.pytest_cache
	@echo "Clean."
