/**
 * Shared vi.mock factory for ../services/api. Every function is a vi.fn() with a
 * harmless default so pages render; individual tests override what they need.
 */
import { vi } from 'vitest'

export function apiMockFactory() {
  const page = { items: [], total: 0, page: 1, page_size: 20 }
  return {
    authApi: { login: vi.fn(), me: vi.fn(), logout: vi.fn(async () => ({ message: 'ok' })) },
    employeesApi: {
      list: vi.fn(async () => page),
      departments: vi.fn(async () => []),
      me: vi.fn(),
      get: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
      setStatus: vi.fn(),
      remove: vi.fn(),
    },
    bannersApi: {
      list: vi.fn(async () => []),
      current: vi.fn(async () => ({ banner: null })),
      get: vi.fn(),
      preview: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
      publish: vi.fn(),
      unpublish: vi.fn(),
      archive: vi.fn(),
      remove: vi.fn(),
    },
    signaturesApi: { get: vi.fn(), mine: vi.fn(), downloadDocument: vi.fn(), outlookInstaller: vi.fn(), sendSetupEmail: vi.fn(), setupLink: vi.fn(), outlookStatus: vi.fn(async () => ({ addin: null, classic_installed_at: null, replace_outlook_signature: false, addin_can_set_default: false })) },
    templatesApi: {
      list: vi.fn(async () => []),
      layouts: vi.fn(async () => []),
      create: vi.fn(),
      update: vi.fn(),
      activate: vi.fn(),
    },
    integrationsApi: {
      nexusStatus: vi.fn(async () => ({ enabled: false, url: null, interval_seconds: 30, synced_fields: [], last_success_at: null, paused: false, last_run: null })),
      nexusSync: vi.fn(),
    },
    overviewApi: { get: vi.fn() },
    auditApi: { list: vi.fn(async () => page) },
    settingsApi: {
      branding: vi.fn(async () => ({ company_name: 'Casterly Private Limited', company_logo_url: '/static/brand/casterly-logo.png', public_base_url: 'https://sig.test' })),
      get: vi.fn(),
      update: vi.fn(),
    },
    uploadsApi: { image: vi.fn() },
  }
}
