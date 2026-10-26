import { ArrowLeft, Pencil, Power, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { EmployeeFormDialog } from '../../components/employees/EmployeeFormDialog'
import { OutlookStatusPanel } from '../../components/signatures/OutlookStatusPanel'
import { SignatureActions } from '../../components/signatures/SignatureActions'
import { SignaturePreview } from '../../components/signatures/SignaturePreview'
import { ActiveBadge, Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import { Avatar, DetailList } from '../../components/ui/Misc'
import { ErrorState, LoadingState } from '../../components/ui/States'
import { useToast } from '../../components/ui/Toast'
import { useEmployee, useEmployeeMutations, useSignature } from '../../hooks/queries'
import { friendlyError } from '../../utils/errors'
import { formatDateTime } from '../../utils/format'

const ext = (url: string | null) =>
  url ? (
    <a href={url} target="_blank" rel="noreferrer" className="text-brand-700 hover:underline">
      {url}
    </a>
  ) : null

export function EmployeeDetailPage() {
  const id = Number(useParams().id)
  const navigate = useNavigate()
  const toast = useToast()
  const employee = useEmployee(id)
  const signature = useSignature(Number.isFinite(id) ? id : null)
  const { setStatus, remove } = useEmployeeMutations()
  const [editing, setEditing] = useState(false)
  const [confirm, setConfirm] = useState<'status' | 'delete' | null>(null)

  if (employee.isLoading) return <LoadingState label="Loading employee..." />
  if (employee.isError || !employee.data)
    return <ErrorState message={friendlyError(employee.error, 'Unable to load this employee.')} onRetry={() => employee.refetch()} />

  const e = employee.data

  async function onConfirm() {
    try {
      if (confirm === 'status') {
        await setStatus.mutateAsync({ id: e.id, active: !e.is_active })
        toast.success(e.is_active ? 'Employee deactivated.' : 'Employee activated.')
      } else if (confirm === 'delete') {
        await remove.mutateAsync(e.id)
        toast.success('Employee deleted.')
        navigate('/admin/employees', { replace: true })
      }
    } catch (err) {
      toast.error(friendlyError(err, 'The action could not be completed.'))
    } finally {
      setConfirm(null)
    }
  }

  return (
    <>
      <Link to="/admin/employees" className="mb-4 inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-800">
        <ArrowLeft className="h-4 w-4" /> Employees
      </Link>

      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <Avatar name={e.full_name} src={e.profile_photo_url} size={56} />
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{e.full_name}</h1>
            <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-slate-500">
              <span>{e.designation}</span>
              <ActiveBadge active={e.is_active} />
              {e.has_login && <Badge tone="blue">Can sign in</Badge>}
            </div>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" icon={<Pencil className="h-4 w-4" />} onClick={() => setEditing(true)}>
            Edit
          </Button>
          <Button variant="secondary" icon={<Power className="h-4 w-4" />} onClick={() => setConfirm('status')}>
            {e.is_active ? 'Deactivate' : 'Activate'}
          </Button>
          <Button variant="ghost" icon={<Trash2 className="h-4 w-4" />} onClick={() => setConfirm('delete')} className="text-red-600 hover:bg-red-50 hover:text-red-700">
            Delete
          </Button>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-5">
        <Card title="Profile" className="xl:col-span-2">
          <DetailList
            items={[
              { label: 'Employee ID', value: <span className="font-mono text-xs">{e.employee_code}</span> },
              { label: 'First name', value: e.first_name },
              { label: 'Last name', value: e.last_name },
              { label: 'Display name', value: e.display_name },
              { label: 'Designation', value: e.designation },
              { label: 'Department', value: e.department },
              { label: 'Company', value: e.company },
              { label: 'Email', value: e.email },
              { label: 'Phone', value: e.phone },
              { label: 'Mobile', value: e.mobile },
              { label: 'Website', value: ext(e.website) },
              { label: 'Address', value: e.address },
              { label: 'LinkedIn', value: ext(e.linkedin_url) },
              { label: 'X / Twitter', value: ext(e.twitter_url) },
              { label: 'Instagram', value: ext(e.instagram_url) },
              { label: 'Other', value: ext(e.other_social_url) },
              { label: 'Updated', value: formatDateTime(e.updated_at) },
            ]}
          />
        </Card>

        <Card
          title="Generated signature"
          description={
            signature.data
              ? signature.data.banner
                ? `Includes the current banner “${signature.data.banner.name}”.`
                : 'No banner is currently published.'
              : undefined
          }
          className="xl:col-span-3"
        >
          <div className="space-y-4">
            <SignatureActions signature={signature.data} canSendEmail />
            <OutlookStatusPanel employeeId={e.id} />
            <SignaturePreview
              html={signature.data?.html}
              loading={signature.isLoading}
              error={signature.isError ? friendlyError(signature.error, 'Unable to generate the signature.') : null}
              recipientName={e.full_name}
              onRetry={() => signature.refetch()}
            />
          </div>
        </Card>
      </div>

      {editing && <EmployeeFormDialog employee={e} onClose={() => setEditing(false)} />}
      <ConfirmDialog
        open={confirm !== null}
        title={confirm === 'delete' ? 'Delete employee?' : e.is_active ? 'Deactivate employee?' : 'Activate employee?'}
        message={
          confirm === 'delete'
            ? `${e.full_name} and their login will be permanently deleted. This cannot be undone.`
            : e.is_active
              ? `${e.full_name} will no longer be able to sign in.`
              : `${e.full_name} will be able to sign in again.`
        }
        confirmLabel={confirm === 'delete' ? 'Delete' : e.is_active ? 'Deactivate' : 'Activate'}
        tone={confirm === 'delete' || e.is_active ? 'danger' : 'primary'}
        loading={setStatus.isPending || remove.isPending}
        onConfirm={onConfirm}
        onCancel={() => setConfirm(null)}
      />
    </>
  )
}
