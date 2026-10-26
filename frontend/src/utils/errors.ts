import { ApiError } from '../services/http'

/**
 * Show the server's message for expected business/validation errors (4xx),
 * otherwise a friendly fallback such as "Unable to publish banner."
 */
export function friendlyError(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    if (error.status === 0) return error.message
    if (error.status >= 400 && error.status < 500 && error.message) return error.message
  }
  return fallback
}

/** Map API validation details onto form field names. */
export function fieldErrors(error: unknown): Record<string, string> {
  if (!(error instanceof ApiError)) return {}
  const out: Record<string, string> = {}
  for (const d of error.details) {
    if (d.field && !out[d.field]) out[d.field] = d.message
  }
  return out
}
