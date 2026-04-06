"""Shared base for all NeuralOps microservices."""
import os
import random
import time
import math
from fastapi import FastAPI, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

def create_app(service_name: str) -> tuple[FastAPI, dict]:
    app = FastAPI(title=service_name)
    chaos = os.getenv("CHAOS_MODE", "false").lower() == "true"

    # Prometheus metrics
    REQUEST_COUNT = Counter(
        "http_requests_total",
        "Total HTTP requests",
        ["service", "method", "endpoint", "status"],
    )
    REQUEST_LATENCY = Histogram(
        "http_request_duration_seconds",
        "HTTP request latency",
        ["service", "endpoint"],
        buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
    )
    ERROR_RATE = Gauge("error_rate_percent", "Current error rate %", ["service"])
    CPU_USAGE = Gauge("cpu_usage_percent", "Simulated CPU usage %", ["service"])
    MEMORY_USAGE = Gauge("memory_usage_percent", "Simulated memory usage %", ["service"])
    RPS = Gauge("requests_per_second", "Requests per second", ["service"])

    metrics = {
        "REQUEST_COUNT": REQUEST_COUNT,
        "REQUEST_LATENCY": REQUEST_LATENCY,
        "ERROR_RATE": ERROR_RATE,
        "CPU_USAGE": CPU_USAGE,
        "MEMORY_USAGE": MEMORY_USAGE,
        "RPS": RPS,
        "service_name": service_name,
        "chaos": chaos,
    }

    @app.get("/health")
    def health():
        return {"status": "ok", "service": service_name, "chaos_mode": chaos}

    @app.get("/metrics")
    def prometheus_metrics():
        # Update simulated system metrics
        if chaos:
            cpu = min(95, 60 + random.uniform(20, 40) + math.sin(time.time() / 10) * 15)
            mem = min(95, 70 + random.uniform(10, 25))
            err = random.uniform(15, 45)
        else:
            cpu = max(5, 20 + random.uniform(-5, 10) + math.sin(time.time() / 30) * 5)
            mem = max(10, 35 + random.uniform(-5, 10))
            err = random.uniform(0, 2)

        CPU_USAGE.labels(service=service_name).set(cpu)
        MEMORY_USAGE.labels(service=service_name).set(mem)
        ERROR_RATE.labels(service=service_name).set(err)
        RPS.labels(service=service_name).set(random.uniform(10, 100) if not chaos else random.uniform(0, 5))

        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app, metrics
