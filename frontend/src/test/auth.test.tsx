import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '../services/api'
import { ApiError } from '../services/http'
import { adminUser, employeeUser, makeEmployee, makeSignature, renderApp } from './utils'

vi.mock('../services/api', async () => (await import('./apiMock')).apiMockFactory())

const mocked = vi.mocked(api, true)

const overview = {
  stats: { total_employees: 0, active_employees: 0, draft_banners: 0, signature_templates: 0, has_published_banner: false },
  current_banner: null,
  active_template: null,
}

beforeEach(() => {
  mocked.overviewApi.get.mockResolvedValue(overview)
})

describe('Login', () => {
  it('signs an admin in and lands on the overview', async () => {
    mocked.authApi.login.mockResolvedValue({
      user: adminUser, employee: null, access_token: 'tok', token_type: 'bearer', expires_at: '2030-01-01T00:00:00Z',
    })
    renderApp('/login')
    const user = userEvent.setup()
    await user.type(screen.getByLabelText(/email/i), 'admin@example.com')
    await user.type(screen.getByLabelText(/^password/i), 'Admin@12345')
    await user.click(screen.getByLabelText(/remember me/i))
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(mocked.authApi.login).toHaveBeenCalledWith('admin@example.com', 'Admin@12345', true)
    expect(await screen.findByRole('heading', { name: 'Overview' })).toBeInTheDocument()
    expect(localStorage.getItem('sigstudio.token')).toBe('tok')
  })

  it('shows the server error on bad credentials', async () => {
    mocked.authApi.login.mockRejectedValue(new ApiError(401, 'INVALID_CREDENTIALS', 'Invalid email or password.'))
    renderApp('/login')
    const user = userEvent.setup()
    await user.type(screen.getByLabelText(/email/i), 'admin@example.com')
    await user.type(screen.getByLabelText(/^password/i), 'wrong')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid email or password.')
  })

  it('validates the email before calling the API', async () => {
    renderApp('/login')
    const user = userEvent.setup()
    await user.type(screen.getByLabelText(/email/i), 'not-an-email')
    await user.type(screen.getByLabelText(/^password/i), 'x')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Enter a valid email address.')
    expect(mocked.authApi.login).not.toHaveBeenCalled()
  })

  it('employees land on their signature page', async () => {
    const emp = makeEmployee()
    mocked.authApi.login.mockResolvedValue({
      user: employeeUser, employee: emp, access_token: 'tok', token_type: 'bearer', expires_at: '2030-01-01T00:00:00Z',
    })
    mocked.signaturesApi.mine.mockResolvedValue(makeSignature(emp))
    renderApp('/login')
    const user = userEvent.setup()
    await user.type(screen.getByLabelText(/email/i), 'rahul@example.com')
    await user.type(screen.getByLabelText(/^password/i), 'secret123')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(await screen.findByRole('heading', { name: 'My Signature' })).toBeInTheDocument()
  })
})

describe('Protected routes', () => {
  it('redirects anonymous users to the login page', async () => {
    renderApp('/admin/banners')
    expect(await screen.findByRole('heading', { name: /sign in to signature studio/i })).toBeInTheDocument()
    expect(mocked.bannersApi.list).not.toHaveBeenCalled()
  })

  it('keeps employees out of admin pages', async () => {
    const emp = makeEmployee()
    mocked.authApi.me.mockResolvedValue({ user: employeeUser, employee: emp })
    mocked.signaturesApi.mine.mockResolvedValue(makeSignature(emp))
    renderApp('/admin/banners', { token: 'tok' })
    expect(await screen.findByRole('heading', { name: 'My Signature' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /banners/i })).not.toBeInTheDocument()
    expect(mocked.bannersApi.list).not.toHaveBeenCalled()
  })

  it('lets admins into admin pages with the admin navigation', async () => {
    mocked.authApi.me.mockResolvedValue({ user: adminUser, employee: null })
    renderApp('/admin/overview', { token: 'tok' })
    expect(await screen.findByRole('heading', { name: 'Overview' })).toBeInTheDocument()
    const nav = screen.getByRole('navigation', { name: 'Main' })
    for (const name of ['Overview', 'Employees', 'Signatures', 'Banners', 'Templates', 'Audit Logs', 'Settings']) {
      expect(within(nav).getByRole('link', { name })).toBeInTheDocument()
    }
  })

  it('returns to login with a message when the stored session is invalid', async () => {
    mocked.authApi.me.mockRejectedValue(new ApiError(401, 'TOKEN_EXPIRED', 'expired'))
    renderApp('/admin/overview', { token: 'old' })
    expect(await screen.findByRole('heading', { name: /sign in/i })).toBeInTheDocument()
    await waitFor(() => expect(sessionStorage.getItem('sigstudio.token')).toBeNull())
  })

  it('logout clears the session', async () => {
    mocked.authApi.me.mockResolvedValue({ user: adminUser, employee: null })
    renderApp('/admin/overview', { token: 'tok' })
    const user = userEvent.setup()
    await user.click(await screen.findByRole('button', { name: 'Logout' }))
    expect(mocked.authApi.logout).toHaveBeenCalled()
    expect(await screen.findByRole('heading', { name: /sign in/i })).toBeInTheDocument()
    expect(sessionStorage.getItem('sigstudio.token')).toBeNull()
  })
})
