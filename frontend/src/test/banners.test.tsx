import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '../services/api'
import { adminUser, makeBanner, makeEmployee, makeSignature, renderApp, stripHtml } from './utils'

vi.mock('../services/api', async () => (await import('./apiMock')).apiMockFactory())
const mocked = vi.mocked(api, true)

beforeEach(() => {
  mocked.authApi.me.mockResolvedValue({ user: adminUser, employee: null })
})

function iframeHtml(container: HTMLElement): string {
  const frame = container.querySelector('iframe')
  return frame?.getAttribute('srcdoc') ?? ''
}

describe('Banner creation & preview', () => {
  async function openEditor() {
    renderApp('/admin/banners', { token: 'tok' })
    const user = userEvent.setup()
    await user.click((await screen.findAllByRole('button', { name: 'Create Banner' }))[0]!)
    const dialog = await screen.findByRole('dialog')
    return { user, d: within(dialog) }
  }

  async function fill(user: ReturnType<typeof userEvent.setup>, d: ReturnType<typeof within>) {
    await user.type(d.getByLabelText(/banner name/i), 'Company Anniversary')
    await user.type(d.getByLabelText(/banner title/i), 'Celebrating 10 Years')
    await user.type(d.getByLabelText(/description/i), 'Thank you for being part of our journey.')
    await user.type(d.getByLabelText(/hosted image url/i), '/uploads/banners/a.png')
  }

  it('requires name, title and image', async () => {
    const { user, d } = await openEditor()
    await user.click(d.getByRole('button', { name: 'Save Draft' }))
    expect(d.getByText('Banner name is required.')).toBeInTheDocument()
    expect(d.getByText('Banner title is required.')).toBeInTheDocument()
    expect(d.getByText('A banner image is required.')).toBeInTheDocument()
    expect(mocked.bannersApi.create).not.toHaveBeenCalled()
  })

  it('rejects an end date before the start date', async () => {
    const { user, d } = await openEditor()
    await fill(user, d)
    await user.type(d.getByLabelText(/start date/i), '2027-01-10T10:00')
    await user.type(d.getByLabelText(/end date/i), '2027-01-05T10:00')
    await user.click(d.getByRole('button', { name: 'Save Draft' }))
    expect(d.getByText('End date must be after the start date.')).toBeInTheDocument()
    expect(mocked.bannersApi.create).not.toHaveBeenCalled()
  })

  it('previews using server-rendered banner HTML', async () => {
    mocked.bannersApi.preview.mockResolvedValue({ html: '<table><tr><td><img alt="Celebrating 10 Years" src="x.png"></td></tr></table>' })
    const { user, d } = await openEditor()
    await fill(user, d)
    await user.click(d.getByRole('button', { name: 'Preview' }))
    expect(mocked.bannersApi.preview).toHaveBeenCalledWith(expect.objectContaining({ name: 'Company Anniversary', image_url: '/uploads/banners/a.png' }))
    const preview = await d.findByTestId('banner-preview')
    expect(iframeHtml(preview)).toContain('alt="Celebrating 10 Years"')
  })

  it('saves a draft', async () => {
    mocked.bannersApi.create.mockResolvedValue(makeBanner())
    const { user, d } = await openEditor()
    await fill(user, d)
    await user.click(d.getByRole('button', { name: 'Save Draft' }))
    expect(mocked.bannersApi.create).toHaveBeenCalledWith({
      name: 'Company Anniversary',
      title: 'Celebrating 10 Years',
      description: 'Thank you for being part of our journey.',
      image_url: '/uploads/banners/a.png',
      target_url: null,
      start_date: null,
      end_date: null,
    })
    expect(await screen.findByText('Banner saved as draft.')).toBeInTheDocument()
  })

  it('publishing from the editor saves, confirms, then publishes', async () => {
    mocked.bannersApi.create.mockResolvedValue(makeBanner({ id: 42 }))
    mocked.bannersApi.publish.mockResolvedValue(makeBanner({ id: 42, status: 'PUBLISHED', effective_status: 'PUBLISHED' }))
    const { user, d } = await openEditor()
    await fill(user, d)
    await user.click(d.getByRole('button', { name: 'Publish' }))

    const confirm = await screen.findByRole('dialog', { name: 'Publish this banner?' })
    expect(within(confirm).getByText('Publishing this banner will make it appear in employee email signatures.')).toBeInTheDocument()
    expect(mocked.bannersApi.publish).not.toHaveBeenCalled()
    await user.click(within(confirm).getByRole('button', { name: 'Publish Banner' }))
    expect(mocked.bannersApi.publish).toHaveBeenCalledWith(42)
    expect(await screen.findByText(/now appears in every employee signature/i)).toBeInTheDocument()
  })
})

describe('Banner history & publish confirmation', () => {
  it('asks for confirmation and warns which banner will be replaced', async () => {
    const live = makeBanner({ id: 1, name: 'Product Launch', status: 'PUBLISHED', effective_status: 'PUBLISHED', is_current: true })
    const draft = makeBanner({ id: 2, name: 'New Year Campaign' })
    mocked.bannersApi.list.mockResolvedValue([stripHtml(live), stripHtml(draft)])
    mocked.bannersApi.get.mockResolvedValue(live)
    mocked.bannersApi.publish.mockResolvedValue({ ...draft, status: 'PUBLISHED' })
    renderApp('/admin/banners', { token: 'tok' })
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Publish New Year Campaign' }))
    const confirm = await screen.findByRole('dialog', { name: 'Publish this banner?' })
    expect(within(confirm).getByText(/“Product Launch” is currently published/)).toBeInTheDocument()

    await user.click(within(confirm).getByRole('button', { name: 'Cancel' }))
    expect(mocked.bannersApi.publish).not.toHaveBeenCalled()

    await user.click(screen.getByRole('button', { name: 'Publish New Year Campaign' }))
    await user.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Publish Banner' }))
    expect(mocked.bannersApi.publish).toHaveBeenCalledWith(2)
  })

  it('only offers valid actions per status', async () => {
    const archived = makeBanner({ id: 3, name: 'Old Promo', status: 'ARCHIVED', effective_status: 'ARCHIVED' })
    mocked.bannersApi.list.mockResolvedValue([stripHtml(archived)])
    renderApp('/admin/banners', { token: 'tok' })
    expect(await screen.findByRole('button', { name: 'Preview Old Promo' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Publish Old Promo' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Edit Old Promo' })).not.toBeInTheDocument()
    expect(screen.getByText('No banner is currently published.')).toBeInTheDocument()
  })
})

describe('Overview: current banner & signature preview', () => {
  it('shows the current banner and an employee signature that includes it', async () => {
    const banner = makeBanner({ status: 'PUBLISHED', effective_status: 'PUBLISHED', is_current: true, published_at: '2026-09-01T10:00:00Z' })
    const rahul = makeEmployee()
    mocked.overviewApi.get.mockResolvedValue({
      stats: { total_employees: 2, active_employees: 2, draft_banners: 1, signature_templates: 1, has_published_banner: true },
      current_banner: banner,
      active_template: null,
    })
    mocked.employeesApi.list.mockResolvedValue({ items: [rahul], total: 1, page: 1, page_size: 200 })
    mocked.signaturesApi.get.mockResolvedValue(makeSignature(rahul, banner))

    renderApp('/admin/overview', { token: 'tok' })
    expect(await screen.findByRole('heading', { name: 'Current Company Banner' })).toBeInTheDocument()
    expect((await screen.findAllByText('Company Anniversary')).length).toBeGreaterThan(0)
    expect(iframeHtml(screen.getByTestId('banner-preview'))).toContain('uploads/banners/a.png')
    expect(screen.getByRole('button', { name: 'Unpublish' })).toBeInTheDocument()

    await vi.waitFor(() => expect(mocked.signaturesApi.get).toHaveBeenCalledWith(rahul.id, undefined))
    await vi.waitFor(() => {
      const html = iframeHtml(screen.getByTestId('signature-preview'))
      expect(html).toContain('Rahul Kumar')
      expect(html).toContain('uploads/banners/a.png')
    })
  })

  it('shows an empty state with a create action when nothing is published', async () => {
    mocked.overviewApi.get.mockResolvedValue({
      stats: { total_employees: 0, active_employees: 0, draft_banners: 0, signature_templates: 0, has_published_banner: false },
      current_banner: null,
      active_template: null,
    })
    renderApp('/admin/overview', { token: 'tok' })
    expect(await screen.findByText('No banner is currently published.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Create Banner' })).toBeInTheDocument()
  })
})
