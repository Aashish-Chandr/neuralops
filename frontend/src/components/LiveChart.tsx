import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, ReferenceLine, CartesianGrid } from 'recharts'
import { format } from 'date-fns'
import type { MetricPoint } from '../types'

interface LiveChartProps {
  data: MetricPoint[]
  color?: string
  threshold?: number
  unit?: string
  height?: number
  yDomain?: [number, number]
}

function Tip({ active, payload, label, unit }: any) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-lg border border-gray-100 bg-white px-3 py-2 text-xs shadow-lg">
      <p className="text-gray-400">{format(new Date(label * 1000), 'HH:mm:ss')}</p>
      <p className="font-mono font-semibold text-gray-900">{payload[0].value?.toFixed(4)}{unit}</p>
    </div>
  )
}

export function LiveChart({ data, color = '#6366f1', threshold, unit = '', height = 110, yDomain }: LiveChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 4, right: 4, left: -24, bottom: 0 }}>
        <defs>
          <linearGradient id={`grad-${color.replace('#','')}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor={color} stopOpacity={0.12} />
            <stop offset="95%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />
        <XAxis dataKey="timestamp" tickFormatter={(t) => format(new Date(t * 1000), 'HH:mm')}
          tick={{ fontSize: 10, fill: '#9ca3af' }} axisLine={false} tickLine={false} interval="preserveStartEnd" />
        <YAxis tick={{ fontSize: 10, fill: '#9ca3af' }} axisLine={false} tickLine={false} domain={yDomain} />
        <Tooltip content={<Tip unit={unit} />} />
        {threshold !== undefined && (
          <ReferenceLine y={threshold} stroke="#ef4444" strokeDasharray="5 3" strokeWidth={1.5}
            label={{ value: 'threshold', position: 'insideTopRight', fontSize: 9, fill: '#ef4444' }} />
        )}
        <Area type="monotone" dataKey="value" stroke={color} strokeWidth={1.5}
          fill={`url(#grad-${color.replace('#','')})`} dot={false} isAnimationActive={false} />
      </AreaChart>
    </ResponsiveContainer>
  )
}
