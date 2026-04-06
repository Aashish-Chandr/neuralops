import type { SystemStats } from '../types'

interface StatProps { label: string; value: string | number; sub?: string; color?: string }

function Stat({ label, value, sub, color = 'text-gray-900' }: StatProps) {
  return (
    <div className="rounded-xl border border-gray-100 bg-white px-5 py-4">
      <p className="text-xs text-gray-400 mb-1">{label}</p>
      <p className={`text-2xl font-bold font-mono ${color}`}>{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  )
}

export function StatsBar({ stats }: { stats: SystemStats }) {
  const hColor = stats.services_healthy === stats.services_total ? 'text-emerald-600'
    : stats.services_healthy > 0 ? 'text-amber-600' : 'text-red-600'
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-3">
      <Stat label="Services Healthy" value={`${stats.services_healthy}/${stats.services_total}`} color={hColor} />
      <Stat label="Predictions" value={stats.total_predictions.toLocaleString()} color="text-indigo-600" />
      <Stat label="Anomalies" value={stats.total_anomalies} color={stats.total_anomalies > 0 ? 'text-red-600' : 'text-emerald-600'} />
      <Stat label="Remediations" value={stats.total_remediations} color="text-violet-600" />
      <Stat label="Uptime" value={`${stats.uptime_percent.toFixed(1)}%`} color={stats.uptime_percent > 99 ? 'text-emerald-600' : 'text-amber-600'} />
    </div>
  )
}
