import { clsx } from 'clsx'

interface CardProps {
  children: React.ReactNode
  className?: string
  alert?: boolean
}

export function Card({ children, className, alert }: CardProps) {
  return (
    <div className={clsx(
      'rounded-xl border bg-white p-5',
      alert ? 'border-red-200 bg-red-50' : 'border-gray-100',
      className
    )}>
      {children}
    </div>
  )
}

export function CardTitle({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-4">
      {children}
    </p>
  )
}
