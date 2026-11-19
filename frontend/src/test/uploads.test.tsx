import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '../services/api'
import { ApiError } from '../services/http'
import { readImageSize } from '../utils/imageSize'
import { UPLOAD_RULES } from './apiMock'
import { adminUser, makeBanner, renderApp, stripHtml } from './utils'

vi.mock('../services/api', async () => (await import('./apiMock')).apiMockFactory())
// jsdom can't decode images, so each test says what size the chosen file is.
vi.mock('../utils/imageSize', () => ({ readImageSize: vi.fn(async () => ({ width: 960, height: 240 })) }))
const mocked = vi.mocked(api, true)
const imageSize = vi.mocked(readImageSize)

beforeEach(() => {
  mocked.authApi.me.mockResolvedValue({ user: adminUser, employee: null })
})

function file(name: string, type: string, bytes = 1024) {
  return new File([new Uint8Array(bytes)], name, { type })
}

async function openBannerEditor(options: Parameters<typeof userEvent.setup>[0] = {}) {
  renderApp('/admin/banners', { token: 'tok' })
  const user = userEvent.setup(options)
  await user.click((await screen.findAllByRole('button', { name: 'Create Banner' }))[0]!)
  const d = within(await screen.findByRole('dialog'))
  return { user, d, input: d.getByLabelText('Upload Banner image') }
}

async function openEmployeeForm() {
  renderApp('/admin/employees', { token: 'tok' })
  const user = userEvent.setup()
  await user.click((await screen.findAllByRole('button', { name: 'Add Employee' }))[0]!)
  const d = within(await screen.findByRole('dialog'))
  return { user, d, input: d.getByLabelText('Upload Photo') }
}

describe('Banner image upload rules', () => {
  it('shows the rule from the backend and offers only JPG and PNG', async () => {
    const { d, input } = await openBannerEditor()
    expect(await d.findByText('Must be exactly 960 x 240 px. JPG or PNG, max 500 KB.')).toBeInTheDocument()
    expect(input).toHaveAttribute('accept', 'image/png,image/jpeg')
    expect(d.queryByLabelText(/hosted image url/i)).not.toBeInTheDocument()  // new images must be uploaded
  })

  it('uploads a 960 x 240 PNG', async () => {
    mocked.uploadsApi.image.mockResolvedValue({ path: '/uploads/banners/new.png', url: 'https://sig.test/uploads/banners/new.png' })
    const { user, d, input } = await openBannerEditor()
    await d.findByText(UPLOAD_RULES.banner.hint)
    const png = file('banner.png', 'image/png')
    await user.upload(input, png)
    expect(mocked.uploadsApi.image).toHaveBeenCalledWith(png, 'banner')
    expect(await d.findByRole('button', { name: 'Replace image' })).toBeInTheDocument()
  })

  it('rejects another size before uploading, saying the required size', async () => {
    imageSize.mockResolvedValueOnce({ width: 1200, height: 300 })
    const { user, d, input } = await openBannerEditor()
    await d.findByText(UPLOAD_RULES.banner.hint)
    await user.upload(input, file('wide.png', 'image/png'))
    expect(await d.findByText('Banner must be exactly 960 x 240 px. Your image is 1200 x 300 px.')).toBeInTheDocument()
    expect(mocked.uploadsApi.image).not.toHaveBeenCalled()
  })

  it('rejects a file over 500 KB, in KB', async () => {
    const { user, d, input } = await openBannerEditor()
    await d.findByText(UPLOAD_RULES.banner.hint)
    await user.upload(input, file('big.png', 'image/png', 742 * 1024))
    expect(await d.findByText('Banner must be 500 KB or smaller. Your file is 742 KB.')).toBeInTheDocument()
    expect(mocked.uploadsApi.image).not.toHaveBeenCalled()
  })

  it('rejects a WebP or GIF file', async () => {
    const { user, d, input } = await openBannerEditor({ applyAccept: false })  // e.g. picked with "All files"
    await d.findByText(UPLOAD_RULES.banner.hint)
    await user.upload(input, file('banner.webp', 'image/webp'))
    expect(await d.findByText('Banner must be a JPG or PNG image. Your file is WebP.')).toBeInTheDocument()
    await user.upload(input, file('banner.gif', 'image/gif'))
    expect(await d.findByText('Banner must be a JPG or PNG image. Your file is GIF.')).toBeInTheDocument()
    expect(mocked.uploadsApi.image).not.toHaveBeenCalled()
  })

  it("shows the backend's message when it rejects the upload", async () => {
    mocked.uploadsApi.image.mockRejectedValue(
      new ApiError(400, 'INVALID_IMAGE_SIZE', 'Banner must be exactly 960 x 240 px. Your image is 961 x 240 px.'),
    )
    const { user, d, input } = await openBannerEditor()
    await d.findByText(UPLOAD_RULES.banner.hint)
    await user.upload(input, file('banner.png', 'image/png'))
    expect(await d.findByText('Banner must be exactly 960 x 240 px. Your image is 961 x 240 px.')).toBeInTheDocument()
  })
})

describe('Employee photo upload rules', () => {
  it('shows the photo rule and rejects a photo under 256 x 256 px', async () => {
    imageSize.mockResolvedValueOnce({ width: 200, height: 180 })
    const { user, d, input } = await openEmployeeForm()
    expect(await d.findByText(/At least 256 x 256 px\. JPG or PNG, max 300 KB\./)).toBeInTheDocument()
    await user.upload(input, file('me.jpg', 'image/jpeg'))
    expect(await d.findByText('Photo must be at least 256 x 256 px. Your image is 200 x 180 px.')).toBeInTheDocument()
    expect(mocked.uploadsApi.image).not.toHaveBeenCalled()
  })

  it('rejects a photo over 300 KB and uploads one that meets the rule', async () => {
    mocked.uploadsApi.image.mockResolvedValue({ path: '/uploads/photos/me.jpg', url: 'https://sig.test/uploads/photos/me.jpg' })
    imageSize.mockResolvedValue({ width: 512, height: 512 })
    const { user, d, input } = await openEmployeeForm()
    await d.findByText(/At least 256 x 256 px/)
    await user.upload(input, file('big.jpg', 'image/jpeg', 301 * 1024))
    expect(await d.findByText('Photo must be 300 KB or smaller. Your file is 301 KB.')).toBeInTheDocument()
    const ok = file('me.jpg', 'image/jpeg', 120 * 1024)
    await user.upload(input, ok)
    expect(mocked.uploadsApi.image).toHaveBeenCalledWith(ok, 'photo')
  })
})

describe('"Not 960 x 240" badge', () => {
  it('marks only older banners whose image is not the required size', async () => {
    mocked.bannersApi.list.mockResolvedValue([
      stripHtml(makeBanner({ id: 1, name: 'Old Promo', meets_size_rule: false })),
      stripHtml(makeBanner({ id: 2, name: 'New Promo', meets_size_rule: true })),
      stripHtml(makeBanner({ id: 3, name: 'Hosted Promo', meets_size_rule: null })),  // size unknown: no badge
    ])
    renderApp('/admin/banners', { token: 'tok' })
    const badge = await screen.findByText('Not 960 x 240')
    expect(screen.getAllByText('Not 960 x 240')).toHaveLength(1)
    expect(badge.closest('tr')).toHaveTextContent('Old Promo')
  })
})

describe('The rules come only from GET /api/uploads/rules', () => {
  it('uses whatever size the backend sends, for the hint, the check and the badge', async () => {
    mocked.uploadsApi.rules.mockResolvedValue({
      ...UPLOAD_RULES,
      banner: { ...UPLOAD_RULES.banner, exact_width: 1200, exact_height: 300, hint: 'Must be exactly 1200 x 300 px. JPG or PNG, max 500 KB.' },
    })
    mocked.bannersApi.list.mockResolvedValue([stripHtml(makeBanner({ name: 'Old Promo', meets_size_rule: false }))])
    const { user, d, input } = await openBannerEditor()
    expect(await d.findByText('Must be exactly 1200 x 300 px. JPG or PNG, max 500 KB.')).toBeInTheDocument()
    await user.upload(input, file('banner.png', 'image/png'))  // 960 x 240: wrong for these rules
    expect(await d.findByText('Banner must be exactly 1200 x 300 px. Your image is 960 x 240 px.')).toBeInTheDocument()
    expect(screen.getByText('Not 1200 x 300')).toBeInTheDocument()
  })
})
