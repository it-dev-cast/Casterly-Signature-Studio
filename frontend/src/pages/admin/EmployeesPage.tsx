import { Eye, Pencil, Plus, Power, Search, Trash2, UserPlus } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'
import { EmployeeFormDialog } from '../../components/employees/EmployeeFormDialog'
import { NexusSyncBar } from '../../components/employees/NexusSyncBar'
import { ActiveBadge, Badge } from '../../components/ui/Badge'
import { Button, IconButton } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import { SelectField } from '../../components/ui/Field'
import { Avatar, PageHeader, Pagination, table } from '../../components/ui/Misc'
import { EmptyState, ErrorState, LoadingState } from '../../components/ui/States'
import { useToast } from '../../components/ui/Toast'
import { useDepartments, useEmployeeMutations, useEmployees } from '../../hooks/queries'
import { useDebounce } from '../../hooks/useDebounce'
import type { Employee } from '../../types/api'
import { friendlyError } from '../../utils/errors'

const PAGE_SIZE = 20

export function EmployeesPage() {
  const toast = useToast()
  const [search, setSearch] = useState('')
  const [department, setDepartment] = useState('')
  const [status, setStatus] = useState<'all' | 'active' | 'inactive'>('all')
  const [page, setPage] = useState(1)
  const q = useDebounce(search.trim(), 300)

  const employees = useEmployees({ q, department, status, page, page_size: PAGE_SIZE })
  const departments = useDepartments()
  const { setStatus: setStatusMutation, remove: removeMutation } = useEmployeeMutations()

  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<Employee | null>(null)
  const [toggling, setToggling] = useState<Employee | null>(null)
  const [deleting, setDeleting] = useState<Employee | null>(null)

  const resetPage = <T,>(fn: (v: T) => void) => (v: T) => {
    fn(v)
    setPage(1)
  }

  async function confirmToggle() {
    if (!toggling) return
    const activate = !toggling.is_active
    try {
      await setStatusMutation.mutateAsync({ id: toggling.id, active: activate })
      toast.success(activate ? `${toggling.full_name} activated.` : `${toggling.full_name} deactivated.`)
    } catch (err) {
      toast.error(friendlyError(err, 'Unable to change the employee status.'))
    } finally {
      setToggling(null)
    }
  }

  async function confirmDelete() {
    if (!deleting) return
    try {
      await removeMutation.mutateAsync(deleting.id)
      toast.success(`${deleting.full_name} was deleted.`)
    } catch (err) {
      toast.error(friendlyError(err, 'Unable to delete the employee.'))
    } finally {
      setDeleting(null)
    }
  }

  const items = employees.data?.items ?? []
  const filtered = !!(q || department || status !== 'all')

  return (
    <>
      <PageHeader
        title="Employees"
        description="Personal details used to generate each employee's signature."
        actions={
          <Button icon={<Plus className="h-4 w-4" />} onClick={() => { setEditing(null); setFormOpen(true) }}>
            Add Employee
          </Button>
        }
      />

      <NexusSyncBar />

      <Card bodyClassName="">
        <div className="flex flex-col gap-3 border-b border-slate-100 p-4 md:flex-row md:items-center">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              type="search"
              autoComplete="off"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1) }}
              placeholder="Search by name, email, ID or designation"
              aria-label="Search employees"
              className="h-10 w-full rounded-lg border border-slate-300 pl-9 pr-3 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
            />
          </div>
          <div className="grid grid-cols-2 gap-3 md:flex">
            <SelectField
              label="Department"
              hideLabel
              value={department}
              onChange={resetPage(setDepartment)}
              containerClassName="md:w-48"
              options={[{ value: '', label: 'All departments' }, ...(departments.data ?? []).map((d) => ({ value: d, label: d }))]}
            />
            <SelectField
              label="Status"
              hideLabel
              value={status}
              onChange={resetPage((v: string) => setStatus(v as typeof status))}
              containerClassName="md:w-40"
              options={[
                { value: 'all', label: 'All statuses' },
                { value: 'active', label: 'Active' },
                { value: 'inactive', label: 'Inactive' },
              ]}
            />
          </div>
        </div>

        {employees.isLoading ? (
          <LoadingState label="Loading employees..." />
        ) : employees.isError ? (
          <ErrorState message={friendlyError(employees.error, 'Unable to load employees.')} onRetry={() => employees.refetch()} />
        ) : items.length === 0 ? (
          <EmptyState
            title="No employees found."
            description={filtered ? 'Try a different search or filter.' : 'Add your first employee to generate their signature.'}
            action={
              !filtered && (
                <Button icon={<UserPlus className="h-4 w-4" />} onClick={() => setFormOpen(true)}>
                  Add Employee
                </Button>
              )
            }
          />
        ) : (
          <>
            <div className={table.wrap}>
              <table className={table.table}>
                <thead className="bg-slate-50/60">
                  <tr>
                    <th className={table.th}>Employee</th>
                    <th className={table.th}>Employee ID</th>
                    <th className={`${table.th} hidden md:table-cell`}>Designation</th>
                    <th className={`${table.th} hidden lg:table-cell`}>Department</th>
                    <th className={`${table.th} hidden xl:table-cell`}>Email</th>
                    <th className={table.th}>Status</th>
                    <th className={`${table.th} text-right`}>Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 bg-surface">
                  {items.map((e) => (
                    <tr key={e.id} className={table.row}>
                      <td className={table.td}>
                        <Link to={`/admin/employees/${e.id}`} className="flex items-center gap-3">
                          <Avatar name={e.full_name} src={e.profile_photo_url} />
                          <div className="min-w-0">
                            <p className="truncate font-medium text-slate-900 hover:text-brand-700">{e.full_name}</p>
                            <p className="truncate text-xs text-slate-500 xl:hidden">{e.email}</p>
                          </div>
                        </Link>
                      </td>
                      <td className={`${table.td} whitespace-nowrap font-mono text-xs`}>{e.employee_code}</td>
                      <td className={`${table.td} hidden md:table-cell`}>{e.designation}</td>
                      <td className={`${table.td} hidden lg:table-cell`}>{e.department ?? '—'}</td>
                      <td className={`${table.td} hidden xl:table-cell`}>{e.email}</td>
                      <td className={table.td}>
                        <div className="flex flex-wrap items-center gap-1.5">
                          <ActiveBadge active={e.is_active} />
                          {e.managed_by_nexus && <Badge tone="blue">nexusAuth</Badge>}
                        </div>
                      </td>
                      <td className={`${table.td} whitespace-nowrap text-right`}>
                        <Link
                          to={`/admin/employees/${e.id}`}
                          className="inline-flex h-8 w-8 items-center justify-center rounded-md text-slate-500 hover:bg-slate-100 hover:text-slate-900"
                          aria-label={`View ${e.full_name}`}
                          title="View"
                        >
                          <Eye className="h-4 w-4" />
                        </Link>
                        <IconButton label={`Edit ${e.full_name}`} onClick={() => { setEditing(e); setFormOpen(true) }}>
                          <Pencil className="h-4 w-4" />
                        </IconButton>
                        {/* A nexusAuth employee is activated, exited and deleted in nexusAuth. */}
                        {!e.managed_by_nexus && (
                          <>
                            <IconButton
                              label={e.is_active ? `Deactivate ${e.full_name}` : `Activate ${e.full_name}`}
                              tone={e.is_active ? 'danger' : 'default'}
                              onClick={() => setToggling(e)}
                            >
                              <Power className="h-4 w-4" />
                            </IconButton>
                            <IconButton label={`Delete ${e.full_name}`} tone="danger" onClick={() => setDeleting(e)}>
                              <Trash2 className="h-4 w-4" />
                            </IconButton>
                          </>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={page} pageSize={PAGE_SIZE} total={employees.data?.total ?? 0} onChange={setPage} />
          </>
        )}
      </Card>

      {formOpen && <EmployeeFormDialog employee={editing} onClose={() => setFormOpen(false)} />}

      <ConfirmDialog
        open={!!toggling}
        title={toggling?.is_active ? 'Deactivate employee?' : 'Activate employee?'}
        message={
          toggling?.is_active
            ? `${toggling?.full_name} will no longer be able to sign in. Their record is kept.`
            : `${toggling?.full_name} will be able to sign in again.`
        }
        confirmLabel={toggling?.is_active ? 'Deactivate' : 'Activate'}
        tone={toggling?.is_active ? 'danger' : 'primary'}
        loading={setStatusMutation.isPending}
        onConfirm={confirmToggle}
        onCancel={() => setToggling(null)}
      >
        {toggling?.is_active && (
          <p className="text-xs text-slate-500">
            Want to remove them completely?{' '}
            <button
              type="button"
              className="font-medium text-red-600 hover:underline"
              onClick={() => {
                setDeleting(toggling)
                setToggling(null)
              }}
            >
              Delete this employee instead
            </button>
          </p>
        )}
      </ConfirmDialog>

      <ConfirmDialog
        open={!!deleting}
        title="Delete employee?"
        message={`${deleting?.full_name ?? ''} and their sign-in will be permanently deleted. Their signature stops working in Outlook. This cannot be undone.`}
        confirmLabel="Delete"
        tone="danger"
        loading={removeMutation.isPending}
        onConfirm={confirmDelete}
        onCancel={() => setDeleting(null)}
      />
    </>
  )
}
