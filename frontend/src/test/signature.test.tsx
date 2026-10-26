import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AppProviders } from '../App'
import { SignaturePreview } from '../components/signatures/SignaturePreview'
import * as api from '../services/api'
import { employeeUser, makeBanner, makeEmployee, makeSignature, renderApp } from './utils'

vi.mock('../services/api', async () => (await import('./apiMock')).apiMockFactory())
const mocked = vi.mocked(api, true)

describe('SignaturePreview', () => {
  it('renders the generated HTML in an isolated frame', () => {
    const { container } = render(
      <AppProviders>
        <SignaturePreview html="<table><tr><td>Priya Sharma</td></tr></table>" recipientName="Priya" />
      </AppProviders>,
    )
    const frame = container.querySelector('iframe')!
    expect(frame.getAttribute('srcdoc')).toContain('Priya Sharma')
    expect(frame.getAttribute('sandbox')).not.toContain('allow-scripts')
  })

  it('shows loading and error states', () => {
    const { rerender } = render(<SignaturePreview loading />)
    expect(screen.getByText('Generating signature...')).toBeInTheDocument()
    rerender(<SignaturePreview error="Unable to generate the signature." />)
    expect(screen.getByRole('alert')).toHaveTextContent('Unable to generate the signature.')
  })
})

describe('Employee signature page', () => {
  const write = vi.fn().mockResolvedValue(undefined)
  const writeText = vi.fn().mockResolvedValue(undefined)

  beforeEach(() => {
    const emp = makeEmployee()
    mocked.authApi.me.mockResolvedValue({ user: employeeUser, employee: emp })
    mocked.signaturesApi.mine.mockResolvedValue(makeSignature(emp, makeBanner({ name: 'New Year Campaign', status: 'PUBLISHED' })))
    Object.defineProperty(navigator, 'clipboard', { value: { write, writeText }, configurable: true })
    vi.stubGlobal('ClipboardItem', class { constructor(public items: Record<string, Blob>) {} })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows my signature with the current company banner', async () => {
    renderApp('/employee/signature', { token: 'tok' })
    expect(await screen.findByRole('heading', { name: 'My Signature' })).toBeInTheDocument()
    expect(await screen.findByText('New Year Campaign')).toBeInTheDocument()
    const html = screen.getByTestId('signature-preview').querySelector('iframe')!.getAttribute('srcdoc')!
    expect(html).toContain('Rahul Kumar')
    expect(html).toContain('Senior Software Developer')
    // Employees get no controls to change the banner.
    expect(screen.queryByRole('button', { name: /publish|unpublish|edit banner/i })).not.toBeInTheDocument()
  })

  it('copies the rendered signature as rich HTML', async () => {
    renderApp('/employee/signature', { token: 'tok' })
    const user = userEvent.setup()
    await screen.findByText('New Year Campaign')
    Object.defineProperty(navigator, 'clipboard', { value: { write, writeText }, configurable: true })
    await user.click(screen.getByRole('button', { name: 'Copy Signature' }))
    expect(write).toHaveBeenCalledTimes(1)
    const item = write.mock.calls[0]![0][0] as { items: Record<string, Blob> }
    expect(Object.keys(item.items)).toEqual(['text/html', 'text/plain'])
    expect(await screen.findByText('Signature copied successfully.')).toBeInTheDocument()
  })

  it('copies the raw HTML', async () => {
    renderApp('/employee/signature', { token: 'tok' })
    const user = userEvent.setup()
    await screen.findByText('New Year Campaign')
    Object.defineProperty(navigator, 'clipboard', { value: { write, writeText }, configurable: true })
    await user.click(screen.getByRole('button', { name: 'Copy HTML' }))
    expect(writeText).toHaveBeenCalledWith(expect.stringContaining('Rahul Kumar'))
  })
})

describe('Copy for Outlook uses the live banner', () => {
  it('copies the version whose banner always shows the published one', async () => {
    const emp = makeEmployee()
    mocked.authApi.me.mockResolvedValue({ user: employeeUser, employee: emp })
    mocked.signaturesApi.mine.mockResolvedValue(makeSignature(emp, makeBanner({ status: 'PUBLISHED' })))
    const writeText = vi.fn().mockResolvedValue(undefined)
    renderApp('/employee/signature', { token: 'tok' })
    const user = userEvent.setup()
    await screen.findByText('Company Anniversary')  // signature loaded, buttons enabled
    // userEvent.setup() installs its own clipboard, so the mock goes in afterwards.
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    await user.click(screen.getByRole('button', { name: 'Copy HTML' }))
    const copied = writeText.mock.calls[0]![0] as string
    expect(copied).toContain('/banner/current.png')
    expect(copied).not.toContain('/uploads/banners/a.png')
  })
})

describe('Install in classic Outlook', () => {
  beforeEach(() => {
    const emp = makeEmployee()
    mocked.authApi.me.mockResolvedValue({ user: employeeUser, employee: emp })
    mocked.signaturesApi.mine.mockResolvedValue(makeSignature(emp))
  })

  it('downloads the personal installer keeping the server-provided file name', async () => {
    const filename = 'Casterly-Signature-Setup_aHR0cDovL2xvY2FsaG9zdDo4MDAw.10.abc123.exe'
    mocked.signaturesApi.outlookInstaller.mockResolvedValue({ blob: new Blob(['MZ']), filename })
    const clicked: string[] = []
    vi.stubGlobal('URL', Object.assign(URL, { createObjectURL: () => 'blob:x', revokeObjectURL: () => {} }))
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (this: HTMLAnchorElement) {
      clicked.push(this.download)
    })

    renderApp('/employee/signature', { token: 'tok' })
    const user = userEvent.setup()
    await user.click(await screen.findByRole('button', { name: 'Install in classic Outlook' }))

    expect(mocked.signaturesApi.outlookInstaller).toHaveBeenCalledWith(10)
    await vi.waitFor(() => expect(clicked).toEqual([filename]))
    expect(await screen.findByText('Installer downloaded. Run it, then restart Outlook.')).toBeInTheDocument()
    click.mockRestore()
  })
})

describe('Signature preview images', () => {
  it('loads images from this app instead of the public address, so previews survive an address change', async () => {
    const { HtmlFrame } = await import('../components/signatures/HtmlFrame')
    const { render } = await import('@testing-library/react')
    const html = '<img src="https://sig.test/uploads/photos/a.jpg"><img src="https://cdn.example.com/b.png">'
    const { container } = render(<AppProviders><HtmlFrame html={html} title="Preview" /></AppProviders>)
    await vi.waitFor(() => {
      const doc = container.querySelector('iframe')!.getAttribute('srcdoc')!
      expect(doc).toContain(`src="${window.location.origin}/uploads/photos/a.jpg"`)
    })
    const doc = container.querySelector('iframe')!.getAttribute('srcdoc')!
    expect(doc).not.toContain('sig.test')
    expect(doc).toContain('src="https://cdn.example.com/b.png"') // other sites are left alone
  })
})
