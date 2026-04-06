import axios from 'axios'
import type {
  ServiceHealth, AnomalyAlert, RemediationAction,
  DriftStatus, ModelInfo, SystemStats, ServiceTimeSeries
} from './types'

const client = axios.create({ baseURL: '/api', timeout: 10000 })

export const api = {
  getSystemStats:      (): Promise<SystemStats>          => client.get('/stats').then(r => r.data),
  getServices:         (): Promise<ServiceHealth[]>      => client.get('/services').then(r => r.data),
  getAlerts:           (): Promise<AnomalyAlert[]>       => client.get('/alerts').then(r => r.data),
  getRemediations:     (): Promise<RemediationAction[]>  => client.get('/remediations').then(r => r.data),
  getDriftStatus:      (): Promise<DriftStatus>          => client.get('/drift').then(r => r.data),
  getModelInfo:        (): Promise<ModelInfo>            => client.get('/model').then(r => r.data),
  getTimeSeries:       (svc: string): Promise<ServiceTimeSeries> =>
    client.get(`/timeseries/${svc}`).then(r => r.data),
  triggerChaos:        (svc: string, enabled: boolean) =>
    client.post(`/chaos/${svc}`, { enabled }).then(r => r.data),
  triggerRetrain:      () => client.post('/retrain').then(r => r.data),
  getAuditLog:         (): Promise<RemediationAction[]>  => client.get('/audit').then(r => r.data),
}
