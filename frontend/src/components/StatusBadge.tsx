import { clsx } from 'clsx'

type Status = 'healthy' | 'degraded' | 'down' | 'anomaly' | 'normal'

const cfg: Record<Status, { dot: string; text: string; label: string }> = {
  healthy:  { dot: 'bg-emerald-500', text: 'text-emerald-700', label: 'Healthy' },
  degraded: { dot: 'bg-amber-400',   text: 'text-amber-700',   label: 'Degraded' },
  down:     { dot: 'bg-red-500',     text: 'text-red-700',     label: 'Down' },
  anomaly:  { dot: 'bg-red-500',     text: 'text-red-700',     label: 'Anomaly' },
  normal:   { dot: 'bg-emerald-500', text: 'text-emerald-700', label: 'Normal' },
}

export function StatusBadge({ status }: { status: Status }) {
  const c = cfg[status]
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={clsx('h-1.5 w-1.5 rounded-full pulse', c.dot)} />
      <span className={clsx('text-xs font-medium', c.text)}>{c.label}</span>
    </span>
  )
}
