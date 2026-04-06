import { useState } from 'react'
import { Zap } from 'lucide-react'
import { clsx } from 'clsx'
import { Card } from './Card'
import { StatusBadge } from './StatusBadge'
import { MetricGauge } from './MetricGauge'
import { api } from '../api'
import type { ServiceHealth } from '../types'

export function ServiceCard({ service, onRefresh }: { service: ServiceHealth; onRefresh?: () => void }) {
  const [toggling, setToggling] = useState(false)
  const isChaos = service.status !== 'healthy'

  const status = service.is_anomaly ? 'anomaly'
    : service.status === 'healthy' ? 'healthy'
    : service.status === 'degraded' ? 'degraded' : 'down'

  async function toggleChaos() {
    setToggling(true)
    try { await api.triggerChaos(service.name, !isChaos); onRefresh?.() }
    finally { setToggling(false) }
  }

  return (
    <Card alert={service.is_anomaly} className="slide-in">
      <div className="flex items-start justify-between mb-4">
        <div>
          <p className="text-sm font-semibold text-gray-900">{service.name}</p>
          <div className="mt-1"><StatusBadge status={status as any} /></div>
        </div>
        <button onClick={toggleChaos} disabled={toggling}
          className={clsx(
            'flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-medium transition-colors',
            isChaos ? 'bg-red-100 text-red-600 hover:bg-red-200' : 'bg-gray-100 text-gray-500 hover:bg-gray-200',
            toggling && 'opacity-40 cursor-not-allowed'
          )}>
          <Zap size={11} />
          {isChaos ? 'Chaos' : 'Normal'}
        </button>
      </div>

      <div className="space-y-2.5">
        <MetricGauge label="CPU" value={service.cpu} warn={60} danger={80} />
        <MetricGauge label="Memory" value={service.memory} warn={65} danger={85} />
        <MetricGauge label="Error Rate" value={service.error_rate} max={100} warn={5} danger={15} />
      </div>

      <div className="mt-4 pt-4 border-t border-gray-100 grid grid-cols-2 gap-3">
        <div>
          <p className="text-xs text-gray-400">Latency P99</p>
          <p className={clsx('text-sm font-mono font-semibold mt-0.5',
            service.latency_p99 > 500 ? 'text-red-600' : service.latency_p99 > 200 ? 'text-amber-600' : 'text-gray-800'
          )}>{service.latency_p99.toFixed(0)}ms</p>
        </div>
        <div>
          <p className="text-xs text-gray-400">RPS</p>
          <p className="text-sm font-mono font-semibold text-indigo-600 mt-0.5">{service.rps.toFixed(1)}</p>
        </div>
      </div>

      {service.is_anomaly && (
        <div className="mt-3 rounded-lg bg-red-100 px-3 py-2">
          <p className="text-xs font-semibold text-red-700">
            Anomaly score: {service.anomaly_score.toFixed(4)}
          </p>
        </div>
      )}
    </Card>
  )
}
