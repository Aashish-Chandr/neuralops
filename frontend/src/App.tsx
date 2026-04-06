import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Activity, RefreshCw, Wifi, WifiOff } from 'lucide-react'
import { StatsBar } from './components/StatsBar'
import { ServiceCard } from './components/ServiceCard'
import { AnomalyScorePanel } from './components/AnomalyScorePanel'
import { RemediationFeed } from './components/RemediationFeed'
import { AlertFeed } from './components/AlertFeed'
import { ModelPanel } from './components/ModelPanel'
import { api } from './api'
import { mockServices, mockAlerts, mockRemediations, mockDrift, mockModel, mockStats } from './mockData'

type Tab = 'overview' | 'services' | 'model' | 'remediations'

export default function App() {
  const [tab, setTab] = useState<Tab>('overview')
  const qc = useQueryClient()

  const statsQ        = useQuery({ queryKey: ['stats'],        queryFn: api.getSystemStats,   refetchInterval: 10000, retry: 1 })
  const servicesQ     = useQuery({ queryKey: ['services'],     queryFn: api.getServices,      refetchInterval: 15000, retry: 1 })
  const alertsQ       = useQuery({ queryKey: ['alerts'],       queryFn: api.getAlerts,        refetchInterval: 10000, retry: 1 })
  const remediationsQ = useQuery({ queryKey: ['remediations'], queryFn: api.getRemediations,  refetchInterval: 15000, retry: 1 })
  const driftQ        = useQuery({ queryKey: ['drift'],        queryFn: api.getDriftStatus,   refetchInterval: 60000, retry: 1 })
  const modelQ        = useQuery({ queryKey: ['model'],        queryFn: api.getModelInfo,     refetchInterval: 60000, retry: 1 })

  const isLive       = statsQ.isSuccess
  const stats        = statsQ.data        ?? mockStats
  const services     = servicesQ.data     ?? mockServices
  const alerts       = alertsQ.data       ?? mockAlerts
  const remediations = remediationsQ.data ?? mockRemediations
  const drift        = driftQ.data        ?? mockDrift
  const model        = modelQ.data        ?? mockModel

  const tabs: { id: Tab; label: string }[] = [
    { id: 'overview',     label: 'Overview' },
    { id: 'services',     label: 'Services' },
    { id: 'model',        label: 'ML Model' },
    { id: 'remediations', label: 'Remediations' },
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-gray-200 bg-white">
        <div className="mx-auto max-w-screen-xl px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-600">
              <Activity size={14} className="text-white" />
            </div>
            <span className="text-sm font-semibold text-gray-900 tracking-tight">NeuralOps</span>
          </div>

          <nav className="flex gap-0.5">
            {tabs.map(t => (
              <button key={t.id} onClick={() => setTab(t.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  tab === t.id ? 'bg-indigo-50 text-indigo-700' : 'text-gray-500 hover:text-gray-900 hover:bg-gray-100'
                }`}>
                {t.label}
              </button>
            ))}
          </nav>

          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1.5 text-xs">
              {isLive
                ? <><Wifi size={11} className="text-emerald-500" /><span className="text-emerald-600">Live</span></>
                : <><WifiOff size={11} className="text-amber-500" /><span className="text-amber-600">Demo</span></>
              }
            </span>
            <button onClick={() => qc.invalidateQueries()}
              className="flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white hover:bg-gray-50 px-3 py-1.5 text-xs text-gray-600 transition-colors">
              <RefreshCw size={11} />
              Refresh
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-screen-xl px-6 py-6 space-y-5">
        <StatsBar stats={stats} />

        {tab === 'overview' && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {services.map(s => (
                <ServiceCard key={s.name} service={s}
                  onRefresh={() => qc.invalidateQueries({ queryKey: ['services'] })} />
              ))}
            </div>
            <AnomalyScorePanel threshold={model.threshold} />
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
              <AlertFeed alerts={alerts} />
              <RemediationFeed actions={remediations} />
            </div>
          </>
        )}

        {tab === 'services' && (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {services.map(s => (
              <ServiceCard key={s.name} service={s}
                onRefresh={() => qc.invalidateQueries({ queryKey: ['services'] })} />
            ))}
          </div>
        )}

        {tab === 'model' && (
          <div className="space-y-5">
            <ModelPanel model={model} drift={drift} />
            <AnomalyScorePanel threshold={model.threshold} />
          </div>
        )}

        {tab === 'remediations' && (
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            <AlertFeed alerts={alerts} />
            <RemediationFeed actions={remediations} />
          </div>
        )}
      </main>
    </div>
  )
}
