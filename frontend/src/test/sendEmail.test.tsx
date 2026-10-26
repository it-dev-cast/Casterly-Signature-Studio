import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '../services/api'
import { ApiError } from '../services/http'
import { adminUser, employeeUser, makeEmployee, makeSignature, renderApp } from './utils'

vi.mock('../services/api', async () => (await import('./apiMock')).apiMockFactory())
const mocked = vi.mocked(api, true)

const rahul = makeEmployee()

beforeEach(() => {
  mocked.authApi.me.mockResolvedValue({ user: adminUser, employee: null })
  mocked.employeesApi.list.mockResolvedValue({ items: [rahul], total: 1, page: 1, page_size: 200 })
  mocked.signaturesApi.get.mockResolvedValue(makeSignature(rahul))
})

async function openSignatures() {
  renderApp('/admin/signatures', { token: 'tok' })
  const user = userEvent.setup()
  const button = await screen.findByRole('button', { name: 'Send email' })
  await vi.waitFor(() => expect(button).toBeEnabled())
  return { user, button }
}

describe('Send email', () => {
  it('sits next to the copy and install buttons on the Signatures page', async () => {
    await openSignatures()
    for (const name of ['Send email', 'Copy Signature', 'Copy HTML', 'Download Signature HTML', 'Install in classic Outlook']) {
      expect(screen.getByRole('button', { name })).toBeInTheDocument()
    }
  })

  it('asks for confirmation, then emails the employee', async () => {
    mocked.signaturesApi.sendSetupEmail.mockResolvedValue({
      employee_id: 10, email: 'rahul@example.com', link: 'https://x/setup/10.k', subject: 's', email_configured: true, sent: true,
    })
    const { user, button } = await openSignatures()
    await user.click(button)
    const dialog = await screen.findByRole('dialog', { name: 'Send signature email?' })
    expect(within(dialog).getByText('rahul@example.com')).toBeInTheDocument()
    expect(mocked.signaturesApi.sendSetupEmail).not.toHaveBeenCalled()

    await user.click(within(dialog).getByRole('button', { name: 'Send email' }))
    expect(mocked.signaturesApi.sendSetupEmail).toHaveBeenCalledWith(10)
    expect(await screen.findByText('Signature email sent to rahul@example.com.')).toBeInTheDocument()
  })

  it('without automatic sending, shows the ready email to copy and send yourself', async () => {
    mocked.signaturesApi.sendSetupEmail.mockRejectedValue(new ApiError(409, 'EMAIL_NOT_CONFIGURED', 'not set up'))
    mocked.signaturesApi.setupLink.mockResolvedValue({
      employee_id: 10, email: 'rahul@example.com', link: 'https://x/setup/10.k', subject: 'Your signature is ready', email_configured: false,
      email_html: '<table><tr><td><a href="https://x/setup/10.k">Set up my signature</a></td></tr></table>',
    })
    const write = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal('ClipboardItem', class { constructor(public items: Record<string, Blob>) {} })
    const { user, button } = await openSignatures()
    await user.click(button)
    await user.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Send email' }))

    const dialog = await screen.findByRole('dialog', { name: 'Send the signature email yourself' })
    expect(within(dialog).getByText('rahul@example.com')).toBeInTheDocument()
    expect(within(dialog).getByText('Your signature is ready')).toBeInTheDocument()
    expect(within(dialog).getByRole('link', { name: /open mail app/i })).toHaveAttribute(
      'href', 'mailto:rahul%40example.com?subject=Your%20signature%20is%20ready',
    )
    expect(dialog.querySelector('iframe')!.getAttribute('srcdoc')).toContain('<a href="https://x/setup/10.k">')

    // Copying happens directly on the click, so the browser allows it.
    Object.defineProperty(navigator, 'clipboard', { value: { write, writeText: vi.fn() }, configurable: true })
    await user.click(within(dialog).getByRole('button', { name: 'Copy email' }))
    const item = write.mock.calls[0]![0][0] as { items: Record<string, Blob> }
    expect(await item.items['text/html']!.text()).toContain('<a href="https://x/setup/10.k">')
    expect(await within(dialog).findByRole('button', { name: 'Email copied' })).toBeInTheDocument()
    vi.unstubAllGlobals()
  })

  it('is not offered to employees on their own page', async () => {
    mocked.authApi.me.mockResolvedValue({ user: employeeUser, employee: rahul })
    mocked.signaturesApi.mine.mockResolvedValue(makeSignature(rahul))
    renderApp('/employee/signature', { token: 'tok' })
    await screen.findByRole('button', { name: 'Copy Signature' })
    expect(screen.queryByRole('button', { name: 'Send email' })).not.toBeInTheDocument()
  })
})
