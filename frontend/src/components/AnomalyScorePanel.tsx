import { useQuery } from '@tanstack/react-query'
import { Card, CardTitle } from './Card'
import { LiveChart } from './LiveChart'
import { api } from '../api'
import { mockTimeSeries } from '../mockData'

const SERVICES = ['user-service', 'order-service', 'payment-service', 'inventory-service', 'notification-service']
const COLORS   = ['#6366f1', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899']

export function AnomalyScorePanel({ threshold }: { threshold: number }) {
  return (
    <Card>
      <CardTitle>Anomaly Score — All Services</CardTitle>
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-6">
        {SERVICES.map((svc, i) => (
          <ServiceChart key={svc} svc={svc} color={COLORS[i]} threshold={threshold} />
        ))}
      </div>
    </Card>
  )
}

function ServiceChart({ svc, color, threshold }: { svc: string; color: string; threshold: number }) {
  const { data } = useQuery({
    queryKey: ['timeseries', svc],
    queryFn: () => api.getTimeSeries(svc),
    refetchInterval: 15000,
    retry: 1,
  })
  const ts = data ?? mockTimeSeries(svc)
  return (
    <div>
      <p className="text-xs font-medium text-gray-600 mb-2">{svc}</p>
      <LiveChart data={ts.anomaly_score} color={color} threshold={threshold}
        height={90} yDomain={[0, Math.max(threshold * 3, 0.15)]} />
    </div>
  )
}
