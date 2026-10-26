/** All timestamps arrive from the API in UTC (ISO 8601) and are shown in the viewer's local time. */

export function formatDateTime(iso: string | null | undefined, empty = '—'): string {
  if (!iso) return empty
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return empty
  return d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

export function formatDate(iso: string | null | undefined, empty = '—'): string {
  if (!iso) return empty
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return empty
  return d.toLocaleDateString(undefined, { dateStyle: 'medium' })
}

/** ISO (UTC) -> value for <input type="datetime-local"> in local time. */
export function toLocalInput(iso: string | null | undefined): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/** <input type="datetime-local"> value (local time) -> ISO string in UTC. */
export function fromLocalInput(value: string): string | null {
  if (!value) return null
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? null : d.toISOString()
}

export function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]!.toUpperCase())
    .join('')
}

export function titleCase(value: string): string {
  return value
    .toLowerCase()
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')
}

/** Uploaded files are stored as '/uploads/...'; in dev these are proxied by Vite. */
export function assetUrl(value: string | null | undefined): string | null {
  if (!value) return null
  if (/^https?:\/\//i.test(value)) return value
  return `${import.meta.env.VITE_API_BASE_URL ?? ''}${value}`
}
