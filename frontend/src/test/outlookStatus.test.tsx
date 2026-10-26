import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '../services/api'
import type { AppSettings, OutlookStatus } from '../types/api'
import { adminUser, makeEmployee, makeSignature, renderApp } from './utils'

vi.mock('../services/api', async () => (await import('./apiMock')).apiMockFactory())
const mocked = vi.mocked(api, true)

const rahul = makeEmployee()
const base: OutlookStatus = { addin: null, classic_installed_at: null, replace_outlook_signature: true, addin_can_set_default: false }

beforeEach(() => {
  mocked.authApi.me.mockResolvedValue({ user: adminUser, employee: null })
  mocked.employeesApi.list.mockResolvedValue({ items: [rahul], total: 1, page: 1, page_size: 200 })
  mocked.signaturesApi.get.mockResolvedValue(makeSignature(rahul))
})

async function panel(status: OutlookStatus) {
  mocked.signaturesApi.outlookStatus.mockResolvedValue(status)
  renderApp('/admin/signatures', { token: 'tok' })
  return within(await screen.findByTestId('outlook-status'))
}

describe('Outlook status panel', () => {
  it('shows a connected add-in that inserted the signature', async () => {
    const p = await panel({
      ...base,
      addin: {
        last_seen_at: '2026-09-25T09:00:00Z', last_source: 'auto', last_status: 'inserted', last_detail: null,
        host: 'OfficeOnline', outlook_display_name: 'Rajatha', outlook_email: 'rajatha18@outlook.com', outlook_default_enabled: false, last_inserted_at: '2026-09-25T09:00:00Z',
      },
    })
    expect(p.getByText(/Outlook add-in connected/)).toBeInTheDocument()
    expect(p.getByText('Rajatha')).toBeInTheDocument()  // the signed-in Outlook user's name
    expect(p.getByText(/Signature inserted/)).toBeInTheDocument()
    expect(p.getByText(/added automatically to each new email/)).toBeInTheDocument()
    // Honest about what Microsoft does not allow add-ins to do.
    expect(p.getByText(/doesn't let add-ins manage them/)).toBeInTheDocument()
  })

  it("explains when the employee's own Outlook default was kept", async () => {
    const p = await panel({
      ...base,
      addin: {
        last_seen_at: '2026-09-25T09:00:00Z', last_source: 'auto', last_status: 'kept_outlook_default', last_detail: null,
        host: 'OfficeOnline', outlook_display_name: 'Rajatha', outlook_email: 'rajatha18@outlook.com', outlook_default_enabled: true, last_inserted_at: null,
      },
    })
    expect(p.getByText(/own default signature in Outlook, so it was kept/)).toBeInTheDocument()
    expect(p.getByText('Signature not inserted yet')).toBeInTheDocument()
  })

  it('reports Outlook errors instead of hiding them', async () => {
    const p = await panel({
      ...base,
      addin: {
        last_seen_at: '2026-09-25T09:00:00Z', last_source: 'button', last_status: 'error',
        last_detail: 'InvalidFormatError: plain text body', host: null, outlook_display_name: null, outlook_email: 'rahul@example.com', outlook_default_enabled: null, last_inserted_at: null,
      },
    })
    expect(p.getByText(/Outlook reported a problem/)).toBeInTheDocument()
    expect(p.getByText('InvalidFormatError: plain text body')).toBeInTheDocument()
  })

  it('shows when nothing has connected yet, and classic installer runs', async () => {
    const p = await panel({ ...base, classic_installed_at: '2026-09-25T08:00:00Z' })
    expect(p.getByText('Outlook add-in not used by this employee yet')).toBeInTheDocument()
    expect(p.getByText(/Classic Outlook installer run/)).toBeInTheDocument()
  })
})

describe('Settings: keep or replace the employee’s own Outlook signature', () => {
  it('defaults to using the Signature Studio signature and saves a change', async () => {
    const settings: AppSettings = {
      company_name: 'Casterly Private Limited', company_website: null, legal_disclaimer: null, show_logo_in_signature: true,
      addin_replace_outlook_signature: true, company_logo_url: '/static/brand/casterly-logo.png',
      public_base_url: 'https://x.example', updated_at: '2026-09-25T00:00:00Z',
    }
    mocked.settingsApi.get.mockResolvedValue(settings)
    mocked.settingsApi.update.mockResolvedValue({ ...settings, addin_replace_outlook_signature: false })
    renderApp('/admin/settings', { token: 'tok' })
    const user = userEvent.setup()
    const toggle = await screen.findByRole('switch', { name: /use the Casterly signature even if an employee has their own default/i })
    expect(toggle).toHaveAttribute('aria-checked', 'true')
    expect(screen.getByText(/takes the place of the employee's own Outlook signature/)).toBeInTheDocument()
    await user.click(toggle)
    await user.click(screen.getByRole('button', { name: 'Save settings' }))
    expect(mocked.settingsApi.update).toHaveBeenCalledWith(expect.objectContaining({ addin_replace_outlook_signature: false }))
    // No instruction to switch Outlook to "(no signature)" anywhere on the page.
    expect(screen.queryByText(/\(no signature\)/)).not.toBeInTheDocument()
  })
})
