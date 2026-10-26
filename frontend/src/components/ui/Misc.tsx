import { ChevronLeft, ChevronRight } from 'lucide-react'
import type { ReactNode } from 'react'
import { assetUrl, initials } from '../../utils/format'

export function PageHeader({ title, description, actions }: { title: string; description?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{title}</h1>
        {description && <p className="mt-1 text-sm text-slate-500">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}

export function Avatar({ name, src, size = 36 }: { name: string; src?: string | null; size?: number }) {
  const url = assetUrl(src)
  const style = { width: size, height: size }
  if (url) return <img src={url} alt="" style={style} className="shrink-0 rounded-full object-cover ring-1 ring-slate-200" />
  return (
    <span
      style={{ ...style, fontSize: size * 0.38 }}
      className="inline-flex shrink-0 items-center justify-center rounded-full bg-brand-100 font-semibold text-brand-700"
      aria-hidden="true"
    >
      {initials(name)}
    </span>
  )
}

interface SegmentedProps<T extends string> {
  value: T
  onChange: (value: T) => void
  options: { value: T; label: string; count?: number }[]
  label: string
}

export function Segmented<T extends string>({ value, onChange, options, label }: SegmentedProps<T>) {
  return (
    <div role="tablist" aria-label={label} className="inline-flex flex-wrap gap-1 rounded-lg bg-slate-100 p-1">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="tab"
          aria-selected={value === o.value}
          onClick={() => onChange(o.value)}
          className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
            value === o.value ? 'bg-surface text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          {o.label}
          {o.count !== undefined && <span className="ml-1.5 text-xs text-slate-400">{o.count}</span>}
        </button>
      ))}
    </div>
  )
}

export function Pagination({ page, pageSize, total, onChange }: { page: number; pageSize: number; total: number; onChange: (p: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / pageSize))
  if (total === 0) return null
  const from = (page - 1) * pageSize + 1
  const to = Math.min(total, page * pageSize)
  return (
    <div className="flex items-center justify-between gap-4 border-t border-slate-100 px-5 py-3 text-sm text-slate-500">
      <span>
        {from}–{to} of {total}
      </span>
      <div className="flex items-center gap-1">
        <button
          type="button"
          className="inline-flex h-8 w-8 items-center justify-center rounded-md hover:bg-slate-100 disabled:opacity-40"
          onClick={() => onChange(page - 1)}
          disabled={page <= 1}
          aria-label="Previous page"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <span className="px-2">
          Page {page} of {pages}
        </span>
        <button
          type="button"
          className="inline-flex h-8 w-8 items-center justify-center rounded-md hover:bg-slate-100 disabled:opacity-40"
          onClick={() => onChange(page + 1)}
          disabled={page >= pages}
          aria-label="Next page"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}

export function DetailList({ items }: { items: { label: string; value: ReactNode }[] }) {
  return (
    <dl className="divide-y divide-slate-100">
      {items.map((i) => (
        <div key={i.label} className="grid grid-cols-3 gap-4 py-2.5 text-sm">
          <dt className="text-slate-500">{i.label}</dt>
          <dd className="col-span-2 min-w-0 break-words text-slate-900">{i.value ?? '—'}</dd>
        </div>
      ))}
    </dl>
  )
}

/** Shared table styles so every data table looks the same. */
export const table = {
  wrap: 'overflow-x-auto',
  table: 'min-w-full divide-y divide-slate-200 text-sm',
  th: 'whitespace-nowrap px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500',
  td: 'px-5 py-3 align-middle text-slate-700',
  row: 'hover:bg-slate-50/70',
}
