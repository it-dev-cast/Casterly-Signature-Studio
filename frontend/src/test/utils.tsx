import { QueryClient } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import type { ReactNode } from 'react'
import { MemoryRouter } from 'react-router'
import { AppProviders } from '../App'
import { AppRoutes } from '../routes/AppRoutes'
import type { Banner, BannerWithHtml, Employee, Signature, User } from '../types/api'

export const adminUser: User = { id: 1, email: 'admin@example.com', role: 'ADMIN', is_active: true }
export const employeeUser: User = { id: 2, email: 'rahul@example.com', role: 'EMPLOYEE', is_active: true }

export function makeEmployee(overrides: Partial<Employee> = {}): Employee {
  return {
    id: 10,
    employee_code: 'EMP-101',
    user_id: 2,
    first_name: 'Rahul',
    last_name: 'Kumar',
    display_name: null,
    full_name: 'Rahul Kumar',
    designation: 'Senior Software Developer',
    department: 'Engineering',
    company: 'Acme',
    email: 'rahul@example.com',
    phone: null,
    mobile: null,
    website: null,
    address: null,
    profile_photo_url: null,
    linkedin_url: null,
    twitter_url: null,
    instagram_url: null,
    other_social_url: null,
    is_active: true,
    has_login: true,
    managed_by_nexus: false,
    nexus_employee_id: null,
    nexus_synced_at: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

export function makeBanner(overrides: Partial<BannerWithHtml> = {}): BannerWithHtml {
  return {
    id: 5,
    name: 'Company Anniversary',
    title: 'Celebrating 10 Years',
    description: 'Thank you for being part of our journey.',
    image_url: '/uploads/banners/a.png',
    image_public_url: 'http://localhost:8000/uploads/banners/a.png',
    target_url: 'https://example.com',
    status: 'DRAFT',
    effective_status: 'DRAFT',
    is_current: false,
    start_date: null,
    end_date: null,
    published_at: null,
    created_by: 1,
    created_by_email: 'admin@example.com',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    html: '<table><tr><td><img src="http://localhost:8000/uploads/banners/a.png" alt="Celebrating 10 Years"></td></tr></table>',
    ...overrides,
  }
}

export function makeSignature(employee = makeEmployee(), banner: BannerWithHtml | null = null): Signature {
  return {
    employee,
    template: null,
    banner,
    html: `<table><tr><td>${employee.full_name}</td><td>${employee.designation}</td></tr>${banner ? `<tr><td>${banner.html}</td></tr>` : ''}</table>`,
    live_html: `<table><tr><td>${employee.full_name}</td></tr><tr><td><img src="http://localhost:8000/banner/current.png"></td></tr></table>`,
    generated_at: '2026-01-01T00:00:00Z',
  }
}

export const stripHtml = (b: BannerWithHtml): Banner => {
  const { html: _html, ...rest } = b
  return rest
}

/** Render the whole app at `route`. Pass `token` to start signed in (authApi.me must be mocked). */
export function renderApp(route: string, { token }: { token?: string } = {}) {
  if (token) sessionStorage.setItem('sigstudio.token', token)
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return render(
    <MemoryRouter initialEntries={[route]}>
      <AppProviders client={client}>
        <AppRoutes />
      </AppProviders>
    </MemoryRouter>,
  )
}

export function Wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return (
    <MemoryRouter>
      <AppProviders client={client}>{children}</AppProviders>
    </MemoryRouter>
  )
}
