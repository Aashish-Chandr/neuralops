# Load Testing

Uses [k6](https://k6.io) — install with `brew install k6` or `choco install k6`.

## Scripts

| Script | Purpose | When to use |
|---|---|---|
| `normal-traffic.js` | Steady realistic traffic across all services | Generating normal training data |
| `spike-test.js` | Sudden 10x surge on payment-service | **Primary demo** — triggers anomaly detection |
| `stress-test.js` | Gradual ramp to find breaking point | Finding system limits |

## Demo Flow

```bash
# 1. Start the full stack
docker-compose -f docker-compose.full.yml up -d

# 2. Generate normal baseline (let this run 10+ min for training data)
k6 run normal-traffic.js

# 3. Enable chaos on payment service, then spike it
CHAOS_PAYMENT=true docker-compose -f docker-compose.full.yml up -d payment-service
k6 run spike-test.js

# Watch Grafana at http://localhost:3000 — anomaly score rises, remediation fires
```

## Expected Demo Timeline

```
0:00  — spike-test starts, normal traffic
1:00  — spike hits, payment errors climb
1:30  — anomaly score crosses threshold in Grafana
1:45  — remediation engine logs: "AUDIT | restart | payment-service"
2:00  — Kubernetes restarts pod
2:30  — anomaly score returns to normal
5:00  — spike-test ends, system healthy
```
