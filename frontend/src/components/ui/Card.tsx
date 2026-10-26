import type { ReactNode } from 'react'

interface CardProps {
  title?: ReactNode
  description?: ReactNode
  actions?: ReactNode
  children?: ReactNode
  className?: string
  bodyClassName?: string
}

export function Card({ title, description, actions, children, className = '', bodyClassName = 'p-5' }: CardProps) {
  return (
    <section className={`rounded-xl border border-slate-200 bg-surface shadow-sm ${className}`}>
      {(title || actions) && (
        <header className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 px-5 py-4">
          <div className="min-w-0">
            {title && <h2 className="text-base font-semibold text-slate-900">{title}</h2>}
            {description && <p className="mt-0.5 text-sm text-slate-500">{description}</p>}
          </div>
          {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
        </header>
      )}
      <div className={bodyClassName}>{children}</div>
    </section>
  )
}

const statTones = {
  brand: 'bg-brand-50 text-brand-600',
  lime: 'bg-lime-soft text-[#6b7a1c]',
  green: 'bg-emerald-50 text-emerald-600',
  amber: 'bg-amber-50 text-amber-600',
  violet: 'bg-brand-100 text-brand-800',
}

interface StatCardProps {
  label: string
  value: ReactNode
  hint?: ReactNode
  icon?: ReactNode
  tone?: keyof typeof statTones
}

export function StatCard({ label, value, hint, icon, tone = 'brand' }: StatCardProps) {
  return (
    <div className="rounded-xl border border-slate-200 bg-surface p-4 shadow-sm transition-shadow hover:shadow-md">
      <div className="flex items-start justify-between gap-3">
        <p className="pt-1 text-sm font-medium text-slate-500">{label}</p>
        {icon && <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${statTones[tone]}`}>{icon}</span>}
      </div>
      <p className="mt-1 truncate text-2xl font-semibold tracking-tight text-slate-900">{value}</p>
      {hint && <p className="mt-1 truncate text-xs text-slate-500">{hint}</p>}
    </div>
  )
}
