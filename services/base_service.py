"""
Shared base for all five microservices.

Each service imports create_app() and gets:
- /health endpoint
- /metrics endpoint (Prometheus format)
- Simulated CPU/memory/error/latency/RPS metrics that update on each scrape
- CHAOS_MODE env var support

The chaos mode is what makes this useful for training. Real anomalies are rare
and hard to label. By deliberately inducing them, we can generate a labeled
dataset and verify that the detection pipeline actually works end-to-end.

The metrics are simulated (not real system metrics) because these are toy services.
In a real deployment you'd use the prometheus-client process_* metrics plus
custom business metrics. The shapes are realistic though — sinusoidal diurnal
patterns for normal, sustained high values with noise for chaos.
"""
import os
import random
import time
import math
from fastapi import FastAPI, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST


def create_app(service_name: str) -> tuple[FastAPI, dict]:
    app   = FastAPI(title=service_name)
    chaos = os.getenv("CHAOS_MODE", "false").lower() == "true"

    REQUEST_COUNT   = Counter(
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
    ERROR_RATE  = Gauge("error_rate_percent",   "Current error rate %",    ["service"])
    CPU_USAGE   = Gauge("cpu_usage_percent",    "Simulated CPU usage %",   ["service"])
    MEMORY      = Gauge("memory_usage_percent", "Simulated memory usage %", ["service"])
    RPS         = Gauge("requests_per_second",  "Requests per second",     ["service"])

    metrics = {
        "REQUEST_COUNT":   REQUEST_COUNT,
        "REQUEST_LATENCY": REQUEST_LATENCY,
        "ERROR_RATE":      ERROR_RATE,
        "CPU_USAGE":       CPU_USAGE,
        "MEMORY_USAGE":    MEMORY,
        "RPS":             RPS,
        "service_name":    service_name,
        "chaos":           chaos,
    }

    @app.get("/health")
    def health():
        return {"status": "ok", "service": service_name, "chaos_mode": chaos}

    @app.get("/metrics")
    def prometheus_metrics():
        t = time.time()
        if chaos:
            cpu = min(95, 60 + random.uniform(20, 40) + math.sin(t / 10) * 15)
            mem = min(95, 70 + random.uniform(10, 25))
            err = random.uniform(15, 45)
            rps = random.uniform(0, 5)
        else:
            cpu = max(5,  20 + random.uniform(-5, 10) + math.sin(t / 30) * 5)
            mem = max(10, 35 + random.uniform(-5, 10))
            err = random.uniform(0, 2)
            rps = random.uniform(10, 100)

        CPU_USAGE.labels(service=service_name).set(cpu)
        MEMORY.labels(service=service_name).set(mem)
        ERROR_RATE.labels(service=service_name).set(err)
        RPS.labels(service=service_name).set(rps)

        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app, metrics
