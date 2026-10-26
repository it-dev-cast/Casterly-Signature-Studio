import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '../services/api'
import { ApiError } from '../services/http'
import { adminUser, makeEmployee, renderApp } from './utils'

vi.mock('../services/api', async () => (await import('./apiMock')).apiMockFactory())
const mocked = vi.mocked(api, true)

beforeEach(() => {
  mocked.authApi.me.mockResolvedValue({ user: adminUser, employee: null })
})

describe('Employee list', () => {
  it('renders employees from the API', async () => {
    mocked.employeesApi.list.mockResolvedValue({
      items: [
        makeEmployee(),
        makeEmployee({ id: 11, employee_code: 'EMP-102', first_name: 'Priya', last_name: 'Sharma', full_name: 'Priya Sharma', designation: 'HR Manager', department: 'Human Resources', email: 'priya@example.com', is_active: false }),
      ],
      total: 2, page: 1, page_size: 20,
    })
    renderApp('/admin/employees', { token: 'tok' })
    const table = await screen.findByRole('table')
    const rows = within(table).getAllByRole('row')
    expect(rows).toHaveLength(3)
    expect(within(rows[1]!).getByText('Rahul Kumar')).toBeInTheDocument()
    expect(within(rows[1]!).getByText('EMP-101')).toBeInTheDocument()
    expect(within(rows[1]!).getByText('Active')).toBeInTheDocument()
    expect(within(rows[2]!).getByText('Priya Sharma')).toBeInTheDocument()
    expect(within(rows[2]!).getByText('Inactive')).toBeInTheDocument()
  })

  it('shows an empty state', async () => {
    renderApp('/admin/employees', { token: 'tok' })
    expect(await screen.findByText('No employees found.')).toBeInTheDocument()
  })

  it('passes the search term to the API', async () => {
    renderApp('/admin/employees', { token: 'tok' })
    const user = userEvent.setup()
    await user.type(await screen.findByLabelText('Search employees'), 'priya')
    await vi.waitFor(() =>
      expect(mocked.employeesApi.list).toHaveBeenLastCalledWith(expect.objectContaining({ q: 'priya', page: 1 })),
    )
  })
})

describe('Employee creation', () => {
  async function openForm() {
    renderApp('/admin/employees', { token: 'tok' })
    const user = userEvent.setup()
    await user.click((await screen.findAllByRole('button', { name: 'Add Employee' }))[0]!)
    return { user, dialog: await screen.findByRole('dialog') }
  }

  it('validates required fields before submitting', async () => {
    const { user, dialog } = await openForm()
    await user.click(within(dialog).getByRole('button', { name: 'Create employee' }))
    expect(await within(dialog).findByText('Employee ID is required.')).toBeInTheDocument()
    expect(within(dialog).getByText('First name is required.')).toBeInTheDocument()
    expect(within(dialog).getByText('Designation is required.')).toBeInTheDocument()
    expect(within(dialog).getByText('Email is required.')).toBeInTheDocument()
    expect(mocked.employeesApi.create).not.toHaveBeenCalled()
  })

  it('creates an employee with the entered details', async () => {
    mocked.employeesApi.create.mockResolvedValue(makeEmployee())
    const { user, dialog } = await openForm()
    const d = within(dialog)
    await user.type(d.getByLabelText(/employee id/i), 'EMP-101')
    await user.type(d.getByLabelText(/first name/i), 'Rahul')
    await user.type(d.getByLabelText(/last name/i), 'Kumar')
    await user.type(d.getByLabelText(/designation/i), 'Senior Software Developer')
    await user.type(d.getByLabelText(/^department/i), 'Engineering')
    await user.type(d.getByLabelText(/^email/i), 'rahul@example.com')
    await user.click(d.getByRole('button', { name: 'Create employee' }))

    expect(mocked.employeesApi.create).toHaveBeenCalledWith(
      expect.objectContaining({
        employee_code: 'EMP-101',
        first_name: 'Rahul',
        last_name: 'Kumar',
        designation: 'Senior Software Developer',
        department: 'Engineering',
        email: 'rahul@example.com',
        phone: null,
        linkedin_url: null,
        is_active: true,
        password: null,
      }),
    )
    expect(await screen.findByText('Employee created.')).toBeInTheDocument()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('shows the address from nexusAuth read-only and never sends it', async () => {
    mocked.employeesApi.create.mockResolvedValue(makeEmployee())
    const { user, dialog } = await openForm()
    const d = within(dialog)
    expect(d.getByLabelText(/^address/i)).toBeDisabled()
    expect(d.getByText(/From nexusAuth\. Add or change it in nexusAuth/)).toBeInTheDocument()
    await user.type(d.getByLabelText(/employee id/i), 'EMP-102')
    await user.type(d.getByLabelText(/first name/i), 'Asha')
    await user.type(d.getByLabelText(/designation/i), 'Engineer')
    await user.type(d.getByLabelText(/^email/i), 'asha@example.com')
    await user.click(d.getByRole('button', { name: 'Create employee' }))
    expect(mocked.employeesApi.create).toHaveBeenCalledWith(expect.not.objectContaining({ address: expect.anything() }))
  })

  it('shows a friendly error when the API rejects the employee', async () => {
    mocked.employeesApi.create.mockRejectedValue(new ApiError(500, 'INTERNAL_ERROR', 'boom'))
    const { user, dialog } = await openForm()
    const d = within(dialog)
    await user.type(d.getByLabelText(/employee id/i), 'EMP-1')
    await user.type(d.getByLabelText(/first name/i), 'A')
    await user.type(d.getByLabelText(/last name/i), 'B')
    await user.type(d.getByLabelText(/designation/i), 'C')
    await user.type(d.getByLabelText(/^email/i), 'a@b.com')
    await user.click(d.getByRole('button', { name: 'Create employee' }))
    expect(await d.findByText('Employee could not be created.')).toBeInTheDocument()
  })
})

describe('Employee deletion', () => {
  beforeEach(() => {
    mocked.employeesApi.list.mockResolvedValue({ items: [makeEmployee()], total: 1, page: 1, page_size: 20 })
    mocked.employeesApi.remove.mockResolvedValue({ deleted: true })
  })

  it('deletes an employee from the list after confirmation', async () => {
    renderApp('/admin/employees', { token: 'tok' })
    const user = userEvent.setup()
    await user.click(await screen.findByRole('button', { name: 'Delete Rahul Kumar' }))
    const dialog = await screen.findByRole('dialog', { name: 'Delete employee?' })
    expect(mocked.employeesApi.remove).not.toHaveBeenCalled()
    await user.click(within(dialog).getByRole('button', { name: 'Delete' }))
    expect(mocked.employeesApi.remove).toHaveBeenCalledWith(10)
    expect(await screen.findByText('Rahul Kumar was deleted.')).toBeInTheDocument()
  })

  it('offers delete from the deactivate dialog', async () => {
    renderApp('/admin/employees', { token: 'tok' })
    const user = userEvent.setup()
    await user.click(await screen.findByRole('button', { name: 'Deactivate Rahul Kumar' }))
    await user.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Delete this employee instead' }))
    const dialog = await screen.findByRole('dialog', { name: 'Delete employee?' })
    await user.click(within(dialog).getByRole('button', { name: 'Delete' }))
    expect(mocked.employeesApi.remove).toHaveBeenCalledWith(10)
    expect(mocked.employeesApi.setStatus).not.toHaveBeenCalled()
  })
})

describe('nexusAuth sync', () => {
  const run = {
    started_at: '2026-09-28T10:00:00Z', finished_at: '2026-09-28T10:00:01Z', ok: true, created: 0, updated: 0,
    deactivated: 0, unchanged: 1, total_remote: 1, error: null, login_rejected: false, problems: [],
  }
  const enabled = {
    enabled: true, url: 'http://127.0.0.1:8000', interval_seconds: 30, synced_fields: [],
    last_success_at: '2026-09-28T10:00:01Z', paused: false, last_run: run,
  }
  const synced = makeEmployee({ managed_by_nexus: true, nexus_employee_id: 7 })

  beforeEach(() => {
    mocked.integrationsApi.nexusStatus.mockResolvedValue(enabled)
    mocked.employeesApi.list.mockResolvedValue({ items: [synced], total: 1, page: 1, page_size: 20 })
  })

  it('shows the sync status and runs a sync on demand', async () => {
    mocked.integrationsApi.nexusSync.mockResolvedValue({ ...enabled, last_run: { ...run, created: 2, updated: 1 } })
    renderApp('/admin/employees', { token: 'tok' })
    expect(await screen.findByText('Employees sync automatically from nexusAuth')).toBeInTheDocument()
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Sync now' }))
    expect(await screen.findByText('Synced: 2 added, 1 updated, 0 deactivated.')).toBeInTheDocument()
    expect(mocked.integrationsApi.nexusSync).toHaveBeenCalled()
  })

  it('marks synced employees and hides deactivate and delete for them', async () => {
    renderApp('/admin/employees', { token: 'tok' })
    const row = within(await screen.findByRole('table')).getAllByRole('row')[1]!
    expect(within(row).getByText('nexusAuth')).toBeInTheDocument()
    expect(within(row).queryByRole('button', { name: 'Delete Rahul Kumar' })).not.toBeInTheDocument()
    expect(within(row).queryByRole('button', { name: 'Deactivate Rahul Kumar' })).not.toBeInTheDocument()
  })

  it('locks the synced fields in the edit form', async () => {
    renderApp('/admin/employees', { token: 'tok' })
    const user = userEvent.setup()
    await user.click(await screen.findByRole('button', { name: 'Edit Rahul Kumar' }))
    const dialog = within(await screen.findByRole('dialog'))
    expect(dialog.getByLabelText(/first name/i)).toBeDisabled()
    expect(dialog.getByLabelText(/^email/i)).toBeDisabled()
    expect(dialog.getByLabelText(/^mobile/i)).not.toBeDisabled()
    expect(dialog.getByText(/This employee comes from nexusAuth/)).toBeInTheDocument()
  })

  it('explains a failed sync', async () => {
    mocked.integrationsApi.nexusStatus.mockResolvedValue({
      ...enabled, paused: true, last_run: { ...run, ok: false, error: 'nexusAuth rejected the sign-in.', login_rejected: true },
    })
    renderApp('/admin/employees', { token: 'tok' })
    expect(await screen.findByText('nexusAuth sync failed')).toBeInTheDocument()
    expect(screen.getByText(/Automatic sync is paused/)).toBeInTheDocument()
  })
})
