import { format } from 'date-fns'
import { AlertTriangle } from 'lucide-react'
import { Card, CardTitle } from './Card'
import type { AnomalyAlert } from '../types'

export function AlertFeed({ alerts }: { alerts: AnomalyAlert[] }) {
  const sorted = [...alerts].sort((a, b) => b.timestamp - a.timestamp).slice(0, 15)
  return (
    <Card>
      <CardTitle>
        <span className="flex items-center gap-2">
          <AlertTriangle size={11} />
          Anomaly Alerts
          {alerts.length > 0 && (
            <span className="ml-auto rounded-full bg-red-100 px-2 py-0.5 text-red-600 text-xs font-semibold">
              {alerts.length}
            </span>
          )}
        </span>
      </CardTitle>
      <div className="space-y-2 overflow-y-auto max-h-72">
        {sorted.length === 0 && (
          <p className="text-xs text-gray-400 text-center py-8">All systems normal</p>
        )}
        {sorted.map((a) => {
          const top = Object.entries(a.top_features).sort(([, x], [, y]) => y - x)[0]
          return (
            <div key={a.id} className="rounded-lg border border-red-100 bg-red-50 p-3">
              <div className="flex justify-between items-center">
                <span className="text-xs font-semibold text-red-700">{a.service}</span>
                <span className="text-xs text-gray-400">{format(new Date(a.timestamp * 1000), 'HH:mm:ss')}</span>
              </div>
              <p className="text-xs text-gray-600 mt-1">
                Score <span className="font-mono font-semibold text-red-600">{a.anomaly_score.toFixed(4)}</span>
                {' '}· threshold {a.threshold.toFixed(4)}
              </p>
              {top && <p className="text-xs text-gray-400 mt-0.5">Top signal: {top[0]}</p>}
            </div>
          )
        })}
      </div>
    </Card>
  )
}
