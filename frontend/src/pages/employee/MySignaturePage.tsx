import { BannerPreview } from '../../components/banners/BannerPreview'
import { SignatureActions } from '../../components/signatures/SignatureActions'
import { SignaturePreview } from '../../components/signatures/SignaturePreview'
import { Card } from '../../components/ui/Card'
import { DetailList, PageHeader } from '../../components/ui/Misc'
import { ErrorState } from '../../components/ui/States'
import { useMySignature } from '../../hooks/queries'
import { friendlyError } from '../../utils/errors'

export function MySignaturePage() {
  const signature = useMySignature()
  const sig = signature.data

  if (signature.isError) {
    return (
      <ErrorState
        message={friendlyError(signature.error, 'Your signature could not be generated. Please contact your administrator.')}
        onRetry={() => signature.refetch()}
      />
    )
  }

  return (
    <>
      <PageHeader title="My Signature" description="Your email signature, generated from your profile and the current company banner." />

      <div className="grid gap-6 xl:grid-cols-3">
        <Card title="Preview" className="xl:col-span-2">
          <div className="space-y-4">
            <SignatureActions signature={sig} />
            <SignaturePreview html={sig?.html} loading={signature.isLoading} recipientName={sig?.employee.full_name} />
          </div>
        </Card>

        <div className="space-y-6">
          <Card title="Current company banner" description="Managed by your administrator.">
            <BannerPreview html={sig?.banner?.html} loading={signature.isLoading} emptyText="No banner is currently published." />
            {sig?.banner && <p className="mt-2 text-sm font-medium text-slate-700">{sig.banner.name}</p>}
          </Card>

          <Card title="My information">
            {sig && (
              <DetailList
                items={[
                  { label: 'Name', value: sig.employee.full_name },
                  { label: 'Designation', value: sig.employee.designation },
                  { label: 'Department', value: sig.employee.department },
                  { label: 'Email', value: sig.employee.email },
                  { label: 'Phone', value: sig.employee.phone ?? sig.employee.mobile },
                ]}
              />
            )}
            <p className="mt-3 text-xs text-slate-500">To change these details, contact your administrator.</p>
          </Card>

          <Card title="How to use it">
            <p className="text-sm font-medium text-slate-800">Outlook (new Outlook and outlook.com / web)</p>
            <ol className="mt-1 list-decimal space-y-1.5 pl-4 text-sm text-slate-600">
              <li>Click <strong>Copy Signature</strong>.</li>
              <li>In Outlook open <strong>Settings (⚙) → Accounts → Signatures</strong>.</li>
              <li>Click <strong>+ Add signature</strong>, name it <strong>Casterly signature</strong>, and paste (Ctrl+V) into the box.</li>
              <li>
                Choose <strong>Casterly signature</strong> for <strong>Default for new messages</strong> and for{' '}
                <strong>Default for replies and forwards</strong>, then <strong>Save</strong>.
              </li>
            </ol>
            <p className="mt-2 text-xs text-slate-500">
              You only do this once, and it stays selected: Signature Studio never switches Outlook back to “No
              signature”. New company banners appear automatically.
            </p>
            <p className="mt-4 text-sm font-medium text-slate-800">Classic Outlook for Windows</p>
            <p className="mt-1 text-sm text-slate-600">
              Click <strong>Install in classic Outlook</strong>, run the downloaded file (don't rename it), then restart
              Outlook.
            </p>
            <p className="mt-4 text-sm font-medium text-slate-800">Gmail</p>
            <p className="mt-1 text-sm text-slate-600">
              Click <strong>Copy Signature</strong>, then paste it in Settings → See all settings → General → Signature.
            </p>
          </Card>
        </div>
      </div>
    </>
  )
}
