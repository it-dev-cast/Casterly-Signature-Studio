import { tokenStorage } from './tokenStorage'

export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? ''

export interface FieldError {
  field: string | null
  message: string
}

export class ApiError extends Error {
  status: number
  code: string
  details: FieldError[]

  constructor(status: number, code: string, message: string, details: FieldError[] = []) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }
}

const SESSION_CODES = new Set(['TOKEN_EXPIRED', 'INVALID_TOKEN', 'TOKEN_REVOKED', 'NOT_AUTHENTICATED'])

let unauthorizedHandler: ((error: ApiError) => void) | null = null

/** Called once by AuthProvider so any 401 anywhere ends the session cleanly. */
export function setUnauthorizedHandler(handler: ((error: ApiError) => void) | null) {
  unauthorizedHandler = handler
}

type Query = Record<string, string | number | boolean | null | undefined>

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: unknown
  query?: Query
  formData?: FormData
  /** Return the raw response text instead of the JSON envelope's `data`. */
  raw?: boolean
}

export function buildUrl(path: string, query?: Query): string {
  const params = new URLSearchParams()
  Object.entries(query ?? {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') params.set(k, String(v))
  })
  const qs = params.toString()
  return `${API_BASE_URL}${path}${qs ? `?${qs}` : ''}`
}

/** Download a file (e.g. the Outlook installer). The server chooses the file name. */
export async function requestFile(path: string): Promise<{ blob: Blob; filename: string | null }> {
  const token = tokenStorage.get()
  let response: Response
  try {
    response = await fetch(buildUrl(path), { headers: token ? { Authorization: `Bearer ${token}` } : {} })
  } catch {
    throw new ApiError(0, 'NETWORK_ERROR', 'Unable to reach the server. Check your connection and try again.')
  }
  if (!response.ok) {
    let err: { code?: string; message?: string } | undefined
    try {
      err = (await response.json())?.error
    } catch {
      err = undefined
    }
    const error = new ApiError(response.status, err?.code ?? 'HTTP_ERROR', err?.message ?? 'The download failed.')
    if (response.status === 401 && token && SESSION_CODES.has(error.code)) unauthorizedHandler?.(error)
    throw error
  }
  const disposition = response.headers.get('Content-Disposition') ?? ''
  const match = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(disposition)
  return { blob: await response.blob(), filename: match ? decodeURIComponent(match[1]!) : null }
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, query, formData, raw } = options
  const headers: Record<string, string> = { Accept: raw ? 'text/html' : 'application/json' }
  const token = tokenStorage.get()
  if (token) headers.Authorization = `Bearer ${token}`
  if (body !== undefined) headers['Content-Type'] = 'application/json'

  let response: Response
  try {
    response = await fetch(buildUrl(path, query), {
      method,
      headers,
      body: formData ?? (body !== undefined ? JSON.stringify(body) : undefined),
    })
  } catch {
    throw new ApiError(0, 'NETWORK_ERROR', 'Unable to reach the server. Check your connection and try again.')
  }

  if (raw && response.ok) return (await response.text()) as T

  let payload: unknown = null
  try {
    payload = await response.json()
  } catch {
    payload = null
  }

  const envelope = payload as { success?: boolean; data?: T; error?: { code: string; message: string; details?: FieldError[] } } | null
  if (response.ok && envelope?.success) return envelope.data as T

  const err = envelope?.error
  const error = new ApiError(
    response.status,
    err?.code ?? 'HTTP_ERROR',
    err?.message ?? 'Something went wrong. Please try again.',
    err?.details ?? [],
  )
  if (response.status === 401 && token && SESSION_CODES.has(error.code)) unauthorizedHandler?.(error)
  throw error
}
