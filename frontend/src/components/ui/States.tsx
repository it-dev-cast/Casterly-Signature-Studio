import { AlertTriangle, Inbox } from 'lucide-react'
import type { ReactNode } from 'react'
import { Button } from './Button'
import { Spinner } from './Spinner'

export function LoadingState({ label = 'Loading...', className = 'py-16' }: { label?: string; className?: string }) {
  return (
    <div className={`flex flex-col items-center justify-center gap-3 text-sm text-slate-500 ${className}`} role="status">
      <Spinner className="h-6 w-6 text-brand-600" />
      <span>{label}</span>
    </div>
  )
}

interface EmptyStateProps {
  title: string
  description?: ReactNode
  action?: ReactNode
  icon?: ReactNode
  className?: string
}

export function EmptyState({ title, description, action, icon, className = 'py-14' }: EmptyStateProps) {
  return (
    <div className={`flex flex-col items-center justify-center px-6 text-center ${className}`}>
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-400">
        {icon ?? <Inbox className="h-6 w-6" />}
      </div>
      <p className="mt-4 text-sm font-semibold text-slate-900">{title}</p>
      {description && <p className="mt-1 max-w-sm text-sm text-slate-500">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}

export function ErrorState({ message, onRetry, className = 'py-14' }: { message: string; onRetry?: () => void; className?: string }) {
  return (
    <div className={`flex flex-col items-center justify-center px-6 text-center ${className}`} role="alert">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-50 text-red-500">
        <AlertTriangle className="h-6 w-6" />
      </div>
      <p className="mt-4 text-sm font-semibold text-slate-900">{message}</p>
      {onRetry && (
        <Button variant="secondary" size="sm" className="mt-4" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  )
}

export function Alert({ tone = 'error', children }: { tone?: 'error' | 'info' | 'warning'; children: ReactNode }) {
  const cls = {
    error: 'border-red-200 bg-red-50 text-red-800',
    info: 'border-brand-200 bg-brand-50 text-brand-800',
    warning: 'border-amber-200 bg-amber-50 text-amber-900',
  }[tone]
  return (
    <div className={`rounded-lg border px-3.5 py-2.5 text-sm ${cls}`} role={tone === 'error' ? 'alert' : 'status'}>
      {children}
    </div>
  )
}
