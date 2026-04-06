import type {
  ServiceHealth, AnomalyAlert, RemediationAction,
  DriftStatus, ModelInfo, SystemStats, ServiceTimeSeries
} from './types'

const SERVICES = ['user-service', 'order-service', 'payment-service', 'inventory-service', 'notification-service']

function rand(min: number, max: number) { return Math.random() * (max - min) + min }

function makeTimeSeries(n = 60, base: number, noise: number, spike = false) {
  const now = Date.now() / 1000
  return Array.from({ length: n }, (_, i) => ({
    timestamp: now - (n - i) * 15,
    value: Math.max(0, base + Math.sin(i / 8) * noise + rand(-noise / 2, noise / 2)
      + (spike && i > 45 ? base * 1.5 : 0)),
  }))
}

export const mockServices: ServiceHealth[] = SERVICES.map((name, i) => ({
  name,
  status: i === 2 ? 'degraded' : 'healthy',
  cpu: i === 2 ? rand(75, 92) : rand(15, 35),
  memory: i === 2 ? rand(70, 88) : rand(30, 50),
  latency_p99: i === 2 ? rand(800, 2000) : rand(50, 150),
  error_rate: i === 2 ? rand(25, 45) : rand(0, 2),
  rps: i === 2 ? rand(1, 5) : rand(30, 80),
  anomaly_score: i === 2 ? rand(0.07, 0.14) : rand(0.005, 0.03),
  is_anomaly: i === 2,
}))

export const mockAlerts: AnomalyAlert[] = [
  {
    id: '1', service: 'payment-service', anomaly_score: 0.0923, threshold: 0.05,
    timestamp: Date.now() / 1000 - 120,
    top_features: { latency_ms: 0.045, error_rate_percent: 0.038, cpu_usage_percent: 0.012 },
    metrics_snapshot: { cpu_usage_percent: 87, error_rate_percent: 38, requests_per_second: 2 },
  },
  {
    id: '2', service: 'payment-service', anomaly_score: 0.0781, threshold: 0.05,
    timestamp: Date.now() / 1000 - 300,
    top_features: { latency_ms: 0.041, error_rate_percent: 0.029 },
    metrics_snapshot: { cpu_usage_percent: 82, error_rate_percent: 31 },
  },
]

export const mockRemediations: RemediationAction[] = [
  {
    id: '1', timestamp: new Date(Date.now() - 90000).toISOString(),
    action: 'restart', service: 'payment-service',
    reason: 'High error rate with low RPS — suspected crash',
    result: 'success', anomaly_score: 0.0923,
  },
  {
    id: '2', timestamp: new Date(Date.now() - 85000).toISOString(),
    action: 'verify_recovery', service: 'payment-service',
    reason: 'Post-remediation health check', result: 'recovered', anomaly_score: 0.0923,
  },
  {
    id: '3', timestamp: new Date(Date.now() - 3600000).toISOString(),
    action: 'scale_up', service: 'order-service',
    reason: 'High CPU/memory/latency — suspected overload',
    result: 'success', anomaly_score: 0.068,
  },
]

export const mockDrift: DriftStatus = {
  drift_fraction: 0.18, drifted_features: 1, threshold: 0.3,
  last_run: new Date(Date.now() - 3600000 * 6).toLocaleString(),
  action: 'none',
  feature_scores: {
    cpu_usage_percent: 0.12, memory_usage_percent: 0.05,
    request_latency_p99: 0.31, error_rate_percent: 0.08, requests_per_second: 0.04,
  },
}

export const mockModel: ModelInfo = {
  name: 'neuralops-lstm-autoencoder', version: '3', stage: 'Production',
  threshold: 0.05, f1_score: 0.891,
  last_trained: new Date(Date.now() - 3600000 * 24 * 2).toLocaleDateString(),
}

export const mockStats: SystemStats = {
  total_predictions: 48320, total_anomalies: 7, total_remediations: 5,
  uptime_percent: 99.7, services_healthy: 4, services_total: 5,
}

export function mockTimeSeries(svc: string): ServiceTimeSeries {
  const isPayment = svc === 'payment-service'
  return {
    service: svc,
    cpu:          makeTimeSeries(60, isPayment ? 80 : 22, 8, isPayment),
    memory:       makeTimeSeries(60, isPayment ? 75 : 36, 5, isPayment),
    latency:      makeTimeSeries(60, isPayment ? 900 : 85, 20, isPayment),
    error_rate:   makeTimeSeries(60, isPayment ? 35 : 1, 2, isPayment),
    anomaly_score: makeTimeSeries(60, isPayment ? 0.08 : 0.015, 0.01, isPayment),
  }
}
