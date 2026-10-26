import { FileImage, ImagePlus, LayoutTemplate, Megaphone, PenLine, UserCheck, UserPlus, Users } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router'
import { CurrentBannerCard } from '../../components/banners/CurrentBannerCard'
import { EmployeePicker } from '../../components/employees/EmployeePicker'
import { SignaturePreview } from '../../components/signatures/SignaturePreview'
import { ButtonLink } from '../../components/ui/Button'
import { Card, StatCard } from '../../components/ui/Card'
import { PageHeader } from '../../components/ui/Misc'
import { ErrorState } from '../../components/ui/States'
import { useOverview, useSignature } from '../../hooks/queries'
import { friendlyError } from '../../utils/errors'

function greeting(date = new Date()): string {
  const h = date.getHours()
  return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening'
}

export function OverviewPage() {
  const navigate = useNavigate()
  const overview = useOverview()
  const [employeeId, setEmployeeId] = useState<number | null>(null)
  const signature = useSignature(employeeId)
  const stats = overview.data?.stats
  const dash = overview.isLoading ? '…' : '—'

  if (overview.isError) {
    return <ErrorState message={friendlyError(overview.error, 'Unable to load the overview.')} onRetry={() => overview.refetch()} />
  }

  return (
    <>
      <PageHeader
        title="Overview"
        description={`${greeting()}. Here's how Casterly's email signatures look right now.`}
        actions={
          <>
            <ButtonLink to="/admin/employees" size="sm" icon={<UserPlus className="h-4 w-4" />}>
              Manage employees
            </ButtonLink>
            <ButtonLink to="/admin/signatures" size="sm" icon={<PenLine className="h-4 w-4" />}>
              Preview signatures
            </ButtonLink>
            <ButtonLink to="/admin/banners?new=1" size="sm" variant="primary" icon={<ImagePlus className="h-4 w-4" />}>
              New banner
            </ButtonLink>
          </>
        }
      />

      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-5">
        <StatCard label="Total Employees" value={stats?.total_employees ?? dash} icon={<Users className="h-4 w-4" />} tone="brand" />
        <StatCard label="Active Employees" value={stats?.active_employees ?? dash} icon={<UserCheck className="h-4 w-4" />} tone="green" />
        <StatCard
          label="Current Banner"
          value={overview.data ? (overview.data.current_banner?.name ?? 'None') : dash}
          hint={overview.data?.current_banner ? 'Live in all signatures' : overview.data ? 'No banner published' : undefined}
          icon={<Megaphone className="h-4 w-4" />}
          tone="lime"
        />
        <StatCard label="Draft Banners" value={stats?.draft_banners ?? dash} icon={<FileImage className="h-4 w-4" />} tone="amber" />
        <StatCard
          label="Signature Templates"
          value={stats?.signature_templates ?? dash}
          hint={overview.data?.active_template ? `Active: ${overview.data.active_template.name}` : undefined}
          icon={<LayoutTemplate className="h-4 w-4" />}
          tone="violet"
        />
      </div>

      <div className="mt-6 space-y-6">
        <CurrentBannerCard
          title="Current Company Banner"
          description="Automatically added to every employee's signature."
          banner={overview.data?.current_banner}
          loading={overview.isLoading}
          showManageLink
          onCreate={() => navigate('/admin/banners?new=1')}
        />

        <Card
          title="Signature Preview"
          description="Employee data + active template + current banner, generated live."
          actions={<EmployeePicker value={employeeId} onChange={setEmployeeId} hideLabel label="Preview employee" className="w-72 max-w-full" />}
        >
          <SignaturePreview
            html={signature.data?.html}
            loading={signature.isLoading && employeeId !== null}
            error={signature.isError ? friendlyError(signature.error, 'Unable to generate the signature.') : null}
            recipientName={signature.data?.employee.full_name}
            onRetry={() => signature.refetch()}
          />
        </Card>
      </div>
    </>
  )
}
