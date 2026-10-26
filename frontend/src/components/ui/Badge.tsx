import type { ReactNode } from 'react'
import type { BannerStatus } from '../../types/api'

export type Tone = 'gray' | 'green' | 'blue' | 'amber' | 'red' | 'violet'

const tones: Record<Tone, string> = {
  gray: 'bg-slate-100 text-slate-700 ring-slate-500/15',
  green: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20',
  blue: 'bg-brand-50 text-brand-700 ring-brand-600/20',
  amber: 'bg-amber-50 text-amber-800 ring-amber-600/20',
  red: 'bg-red-50 text-red-700 ring-red-600/20',
  violet: 'bg-lime-soft text-[#5b6817] ring-lime-accent/60',
}

export function Badge({ tone = 'gray', children, dot }: { tone?: Tone; children: ReactNode; dot?: boolean }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${tones[tone]}`}>
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />}
      {children}
    </span>
  )
}

const bannerTones: Record<BannerStatus, Tone> = {
  DRAFT: 'gray',
  SCHEDULED: 'violet',
  PUBLISHED: 'green',
  EXPIRED: 'amber',
  ARCHIVED: 'red',
}

const bannerLabels: Record<BannerStatus, string> = {
  DRAFT: 'Draft',
  SCHEDULED: 'Scheduled',
  PUBLISHED: 'Published',
  EXPIRED: 'Expired',
  ARCHIVED: 'Archived',
}

export function BannerStatusBadge({ status }: { status: BannerStatus }) {
  return (
    <Badge tone={bannerTones[status]} dot>
      {bannerLabels[status]}
    </Badge>
  )
}

export function ActiveBadge({ active, activeLabel = 'Active', inactiveLabel = 'Inactive' }: { active: boolean; activeLabel?: string; inactiveLabel?: string }) {
  return (
    <Badge tone={active ? 'green' : 'gray'} dot>
      {active ? activeLabel : inactiveLabel}
    </Badge>
  )
}
