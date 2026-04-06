import { clsx } from 'clsx'

interface MetricGaugeProps {
  label: string
  value: number
  unit?: string
  max?: number
  warn?: number
  danger?: number
}

export function MetricGauge({ label, value, unit = '%', max = 100, warn = 60, danger = 80 }: MetricGaugeProps) {
  const pct = Math.min((value / max) * 100, 100)
  const color = value >= danger ? 'bg-red-400' : value >= warn ? 'bg-amber-400' : 'bg-emerald-400'
  const textColor = value >= danger ? 'text-red-600' : value >= warn ? 'text-amber-600' : 'text-gray-700'

  return (
    <div className="space-y-1.5">
      <div className="flex justify-between">
        <span className="text-xs text-gray-500">{label}</span>
        <span className={clsx('text-xs font-mono font-medium', textColor)}>
          {value.toFixed(1)}{unit}
        </span>
      </div>
      <div className="h-1 w-full rounded-full bg-gray-100">
        <div className={clsx('h-1 rounded-full transition-all duration-500', color)} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}
