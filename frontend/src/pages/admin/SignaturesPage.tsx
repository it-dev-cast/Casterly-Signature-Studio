import { useState } from 'react'
import { BannerPreview } from '../../components/banners/BannerPreview'
import { EmployeePicker } from '../../components/employees/EmployeePicker'
import { OutlookStatusPanel } from '../../components/signatures/OutlookStatusPanel'
import { HtmlCode, SignatureActions } from '../../components/signatures/SignatureActions'
import { SignaturePreview } from '../../components/signatures/SignaturePreview'
import { Card } from '../../components/ui/Card'
import { SelectField } from '../../components/ui/Field'
import { PageHeader, Segmented } from '../../components/ui/Misc'
import { useSignature, useTemplates } from '../../hooks/queries'
import { friendlyError } from '../../utils/errors'
import { formatDateTime } from '../../utils/format'

export function SignaturesPage() {
  const [employeeId, setEmployeeId] = useState<number | null>(null)
  const [templateId, setTemplateId] = useState<number | undefined>(undefined)
  const [view, setView] = useState<'preview' | 'html'>('preview')
  const templates = useTemplates()
  const signature = useSignature(employeeId, templateId)
  const sig = signature.data

  const activeTemplate = templates.data?.find((t) => t.is_active)
  const templateOptions = [
    { value: '', label: activeTemplate ? `Active template (${activeTemplate.name})` : 'Active template' },
    ...(templates.data ?? []).filter((t) => !t.is_active).map((t) => ({ value: String(t.id), label: t.name })),
  ]

  return (
    <>
      <PageHeader
        title="Signatures"
        description="Preview, copy or download any employee's generated email signature."
      />

      <div className="grid gap-6 xl:grid-cols-3">
        <div className="space-y-6">
          <Card title="Signature builder">
            <div className="space-y-4">
              <EmployeePicker value={employeeId} onChange={setEmployeeId} />
              <SelectField
                label="Template"
                value={templateId ? String(templateId) : ''}
                onChange={(v) => setTemplateId(v ? Number(v) : undefined)}
                options={templateOptions}
                hint="Previewing a non-active template does not change what employees use."
              />
            </div>
          </Card>

          <Card title="Current banner" description="Added automatically from the published banner.">
            <BannerPreview html={sig?.banner?.html} loading={signature.isLoading && employeeId !== null} emptyText="No banner is currently published." />
            {sig?.banner && <p className="mt-2 text-sm font-medium text-slate-700">{sig.banner.name}</p>}
          </Card>
        </div>

        <Card
          className="xl:col-span-2"
          title={sig ? sig.employee.full_name : 'Signature'}
          description={sig ? `Generated ${formatDateTime(sig.generated_at)} · ${sig.template?.name ?? 'Default design'}` : undefined}
          actions={
            <Segmented
              label="Signature view"
              value={view}
              onChange={setView}
              options={[
                { value: 'preview', label: 'Preview' },
                { value: 'html', label: 'HTML' },
              ]}
            />
          }
        >
          <div className="space-y-4">
            <SignatureActions signature={sig} templateId={templateId} canSendEmail />
            <OutlookStatusPanel employeeId={employeeId} />
            {view === 'preview' ? (
              <SignaturePreview
                html={sig?.html}
                loading={signature.isLoading && employeeId !== null}
                error={signature.isError ? friendlyError(signature.error, 'Unable to generate the signature.') : null}
                recipientName={sig?.employee.full_name}
                onRetry={() => signature.refetch()}
              />
            ) : sig ? (
              <HtmlCode html={sig.html} />
            ) : (
              <p className="py-10 text-center text-sm text-slate-500">Select an employee to view the HTML.</p>
            )}
          </div>
        </Card>
      </div>
    </>
  )
}
