import { useState } from 'react'
import { RefreshCw } from 'lucide-react'
import { Card, CardTitle } from './Card'
import { api } from '../api'
import type { ModelInfo, DriftStatus } from '../types'

export function ModelPanel({ model, drift }: { model: ModelInfo; drift: DriftStatus }) {
  const [loading, setLoading] = useState(false)
  const [msg, setMsg] = useState('')

  async function retrain() {
    setLoading(true); setMsg('')
    try { await api.triggerRetrain(); setMsg('Retraining pipeline triggered') }
    catch { setMsg('Failed to trigger retrain') }
    finally { setLoading(false) }
  }

  const driftPct = (drift.drift_fraction * 100).toFixed(1)
  const driftOver = drift.drift_fraction >= drift.threshold
  const driftColor = driftOver ? 'text-red-600' : drift.drift_fraction >= drift.threshold * 0.7 ? 'text-amber-600' : 'text-emerald-600'

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <Card>
        <CardTitle>ML Model</CardTitle>
        <div className="space-y-3">
          {[
            ['Model',        model.name],
            ['Version',      `v${model.version}`],
            ['Stage',        model.stage],
            ['Threshold',    model.threshold.toFixed(4)],
            ['F1 Score',     `${(model.f1_score * 100).toFixed(1)}%`],
            ['Last Trained', model.last_trained],
          ].map(([k, v]) => (
            <div key={k} className="flex justify-between items-center">
              <span className="text-xs text-gray-400">{k}</span>
              <span className="text-xs font-mono font-medium text-gray-800">{v}</span>
            </div>
          ))}
        </div>
      </Card>

      <Card alert={driftOver}>
        <CardTitle>Model Drift</CardTitle>
        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-xs text-gray-400">Drift Fraction</span>
            <span className={`text-xl font-bold font-mono ${driftColor}`}>{driftPct}%</span>
          </div>
          <div className="space-y-1">
            <div className="h-1.5 w-full rounded-full bg-gray-100">
              <div className={`h-1.5 rounded-full transition-all duration-500 ${driftOver ? 'bg-red-400' : 'bg-indigo-400'}`}
                style={{ width: `${Math.min(drift.drift_fraction * 100, 100)}%` }} />
            </div>
            <div className="flex justify-between text-xs text-gray-400">
              <span>0%</span>
              <span>threshold {(drift.threshold * 100).toFixed(0)}%</span>
              <span>100%</span>
            </div>
          </div>
          {[
            ['Drifted Features', `${drift.drifted_features} / 5`],
            ['Last Check',       drift.last_run],
            ['Action',           drift.action === 'retrain_triggered' ? 'Retrain triggered' : 'No action'],
          ].map(([k, v]) => (
            <div key={k} className="flex justify-between">
              <span className="text-xs text-gray-400">{k}</span>
              <span className="text-xs font-medium text-gray-700">{v}</span>
            </div>
          ))}
          <button onClick={retrain} disabled={loading}
            className="w-full flex items-center justify-center gap-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 px-3 py-2 text-xs font-semibold text-white transition-colors mt-2">
            <RefreshCw size={11} className={loading ? 'animate-spin' : ''} />
            {loading ? 'Triggering...' : 'Trigger Retrain'}
          </button>
          {msg && <p className="text-xs text-center text-gray-500">{msg}</p>}
        </div>
      </Card>
    </div>
  )
}
