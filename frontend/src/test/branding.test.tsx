import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '../services/api'
import type { AppSettings } from '../types/api'
import { adminUser, renderApp } from './utils'

vi.mock('../services/api', async () => (await import('./apiMock')).apiMockFactory())
const mocked = vi.mocked(api, true)

const LOGO = 'http://localhost:8000/static/brand/casterly-logo.png'

const settings: AppSettings = {
  company_name: 'Casterly Private Limited',
  company_website: null,
  legal_disclaimer: null,
  show_logo_in_signature: true,
  addin_replace_outlook_signature: true,
  company_logo_url: LOGO,
  public_base_url: 'http://localhost:8000',
  updated_at: '2026-09-24T00:00:00Z',
}

beforeEach(() => {
  mocked.settingsApi.branding.mockResolvedValue({ company_name: 'Casterly Private Limited', company_logo_url: LOGO, public_base_url: 'https://sig.test' })
})

describe('Company branding', () => {
  it('shows the company logo and name on the sign-in page', async () => {
    renderApp('/login')
    const logo = await screen.findByRole('img', { name: 'Casterly Private Limited logo' })
    expect(logo).toHaveAttribute('src', LOGO)
    expect(screen.getByText('Casterly Private Limited')).toBeInTheDocument()
  })

  it('shows the company name in the app sidebar', async () => {
    mocked.authApi.me.mockResolvedValue({ user: adminUser, employee: null })
    mocked.overviewApi.get.mockResolvedValue({
      stats: { total_employees: 0, active_employees: 0, draft_banners: 0, signature_templates: 0, has_published_banner: false },
      current_banner: null,
      active_template: null,
    })
    renderApp('/admin/overview', { token: 'tok' })
    expect((await screen.findAllByText('Casterly Private Limited')).length).toBeGreaterThan(0)
  })
})

describe('Settings: logo in signatures', () => {
  beforeEach(() => {
    mocked.authApi.me.mockResolvedValue({ user: adminUser, employee: null })
    mocked.settingsApi.get.mockResolvedValue(settings)
  })

  it('shows the built-in logo read-only, with no way to upload a different one', async () => {
    renderApp('/admin/settings', { token: 'tok' })
    expect(await screen.findByRole('img', { name: 'Casterly Private Limited logo' })).toHaveAttribute('src', LOGO)
    expect(screen.queryByLabelText(/upload company logo/i)).not.toBeInTheDocument()
    expect(screen.getByRole('switch', { name: 'Show logo in email signatures' })).toHaveAttribute('aria-checked', 'true')
  })

  it('switches the logo off and saves the setting', async () => {
    mocked.settingsApi.update.mockResolvedValue({ ...settings, show_logo_in_signature: false })
    renderApp('/admin/settings', { token: 'tok' })
    const user = userEvent.setup()
    const toggle = await screen.findByRole('switch', { name: 'Show logo in email signatures' })
    await user.click(toggle)
    expect(toggle).toHaveAttribute('aria-checked', 'false')
    await user.click(screen.getByRole('button', { name: 'Save settings' }))
    expect(mocked.settingsApi.update).toHaveBeenCalledWith({
      company_name: 'Casterly Private Limited',
      company_website: null,
      legal_disclaimer: null,
      show_logo_in_signature: false,
      addin_replace_outlook_signature: true,
    })
    expect(await screen.findByText('Settings saved.')).toBeInTheDocument()
  })
})
