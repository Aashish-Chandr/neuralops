export interface ServiceHealth {
  name: string
  status: 'healthy' | 'degraded' | 'down'
  cpu: number
  memory: number
  latency_p99: number
  error_rate: number
  rps: number
  anomaly_score: number
  is_anomaly: boolean
}

export interface AnomalyAlert {
  id: string
  service: string
  anomaly_score: number
  threshold: number
  timestamp: number
  top_features: Record<string, number>
  metrics_snapshot: Record<string, number>
}

export interface RemediationAction {
  id: string
  timestamp: string
  action: 'restart' | 'scale_up' | 'rollback' | 'escalate' | 'verify_recovery'
  service: string
  reason: string
  result: 'success' | 'failed' | 'escalated' | 'recovered'
  anomaly_score: number
}

export interface DriftStatus {
  drift_fraction: number
  drifted_features: number
  threshold: number
  last_run: string
  action: 'none' | 'retrain_triggered'
  feature_scores: Record<string, number>
}

export interface ModelInfo {
  name: string
  version: string
  stage: string
  threshold: number
  f1_score: number
  last_trained: string
}

export interface SystemStats {
  total_predictions: number
  total_anomalies: number
  total_remediations: number
  uptime_percent: number
  services_healthy: number
  services_total: number
}

export interface MetricPoint {
  timestamp: number
  value: number
}

export interface ServiceTimeSeries {
  service: string
  cpu: MetricPoint[]
  memory: MetricPoint[]
  latency: MetricPoint[]
  error_rate: MetricPoint[]
  anomaly_score: MetricPoint[]
}
