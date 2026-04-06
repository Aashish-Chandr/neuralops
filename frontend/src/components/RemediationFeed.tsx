import { format } from 'date-fns'
import { clsx } from 'clsx'
import { RotateCcw, TrendingUp, ArrowLeftRight, AlertTriangle, CheckCircle } from 'lucide-react'
import { Card, CardTitle } from './Card'
import type { RemediationAction } from '../types'

const ACTION = {
  restart:         { icon: RotateCcw,      color: 'text-indigo-600',  bg: 'bg-indigo-50',  label: 'Pod Restart' },
  scale_up:        { icon: TrendingUp,     color: 'text-violet-600',  bg: 'bg-violet-50',  label: 'Scale Up' },
  rollback:        { icon: ArrowLeftRight, color: 'text-amber-600',   bg: 'bg-amber-50',   label: 'Rollback' },
  escalate:        { icon: AlertTriangle,  color: 'text-red-600',     bg: 'bg-red-50',     label: 'Escalated' },
  verify_recovery: { icon: CheckCircle,    color: 'text-emerald-600', bg: 'bg-emerald-50', label: 'Recovered' },
}

export function RemediationFeed({ actions }: { actions: RemediationAction[] }) {
  const sorted = [...actions].sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
  return (
    <Card>
      <CardTitle>Remediation Timeline</CardTitle>
      <div className="space-y-2 overflow-y-auto max-h-72">
        {sorted.length === 0 && (
          <p className="text-xs text-gray-400 text-center py-8">No actions taken yet</p>
        )}
        {sorted.map((a) => {
          const c = ACTION[a.action] ?? ACTION.restart
          const Icon = c.icon
          return (
            <div key={a.id} className={clsx('flex items-start gap-3 rounded-lg p-3', c.bg)}>
              <Icon size={13} className={clsx('mt-0.5 shrink-0', c.color)} />
              <div className="flex-1 min-w-0">
                <div className="flex justify-between items-center gap-2">
                  <span className={clsx('text-xs font-semibold', c.color)}>{c.label}</span>
                  <span className="text-xs text-gray-400 shrink-0">
                    {format(new Date(a.timestamp), 'HH:mm:ss')}
                  </span>
                </div>
                <p className="text-xs text-gray-700 truncate">{a.service}</p>
                <p className="text-xs text-gray-400 truncate">{a.reason}</p>
              </div>
              <span className={clsx(
                'shrink-0 rounded px-1.5 py-0.5 text-xs font-medium',
                a.result === 'success' || a.result === 'recovered'
                  ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'
              )}>{a.result}</span>
            </div>
          )
        })}
      </div>
    </Card>
  )
}
