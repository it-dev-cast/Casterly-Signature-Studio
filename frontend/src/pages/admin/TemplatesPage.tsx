import { CheckCircle2, Pencil, Plus } from 'lucide-react'
import { useState } from 'react'
import { EmployeePicker } from '../../components/employees/EmployeePicker'
import { SignaturePreview } from '../../components/signatures/SignaturePreview'
import { TemplateFormDialog } from '../../components/templates/TemplateFormDialog'
import { Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { PageHeader } from '../../components/ui/Misc'
import { EmptyState, ErrorState, LoadingState } from '../../components/ui/States'
import { useToast } from '../../components/ui/Toast'
import { useSignature, useTemplateMutations, useTemplates } from '../../hooks/queries'
import type { SignatureTemplate } from '../../types/api'
import { friendlyError } from '../../utils/errors'

export function TemplatesPage() {
  const toast = useToast()
  const templates = useTemplates()
  const { activate } = useTemplateMutations()
  const [form, setForm] = useState<{ template: SignatureTemplate | null } | null>(null)
  const [selected, setSelected] = useState<number | null>(null)
  const [employeeId, setEmployeeId] = useState<number | null>(null)

  const list = templates.data ?? []
  const selectedTemplate = list.find((t) => t.id === selected) ?? list.find((t) => t.is_active) ?? list[0]
  const signature = useSignature(employeeId, selectedTemplate?.id)

  async function doActivate(t: SignatureTemplate) {
    try {
      await activate.mutateAsync(t.id)
      toast.success(`“${t.name}” is now the active template for all signatures.`)
    } catch (err) {
      toast.error(friendlyError(err, 'Unable to activate the template.'))
    }
  }

  return (
    <>
      <PageHeader
        title="Templates"
        description="The active template is used for every employee signature."
        actions={
          <Button icon={<Plus className="h-4 w-4" />} onClick={() => setForm({ template: null })}>
            New Template
          </Button>
        }
      />

      {templates.isLoading ? (
        <LoadingState label="Loading templates..." />
      ) : templates.isError ? (
        <ErrorState message={friendlyError(templates.error, 'Unable to load templates.')} onRetry={() => templates.refetch()} />
      ) : list.length === 0 ? (
        <Card>
          <EmptyState
            title="No signature templates."
            description="Signatures use the built-in default design until you create a template."
            action={<Button onClick={() => setForm({ template: null })}>New Template</Button>}
          />
        </Card>
      ) : (
        <div className="grid gap-6 xl:grid-cols-5">
          <div className="space-y-3 xl:col-span-2">
            {list.map((t) => (
              <div
                key={t.id}
                onClick={() => setSelected(t.id)}
                className={`w-full cursor-pointer rounded-xl border bg-surface p-4 text-left shadow-sm transition-colors ${
                  selectedTemplate?.id === t.id ? 'border-brand-500 ring-2 ring-brand-500/15' : 'border-slate-200 hover:border-slate-300'
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <button
                      type="button"
                      onClick={() => setSelected(t.id)}
                      aria-pressed={selectedTemplate?.id === t.id}
                      className="font-semibold text-slate-900 hover:text-brand-700"
                    >
                      {t.name}
                    </button>
                    <p className="mt-0.5 text-sm text-slate-500">{t.description ?? 'No description'}</p>
                  </div>
                  {t.is_active ? <Badge tone="green" dot>Active</Badge> : <Badge>{t.layout}</Badge>}
                </div>
                <div className="mt-3 flex items-center gap-2 text-xs text-slate-500">
                  <span className="h-4 w-4 rounded-full ring-1 ring-slate-200" style={{ background: t.primary_color }} />
                  <span className="h-4 w-4 rounded-full ring-1 ring-slate-200" style={{ background: t.accent_color }} />
                  <span className="ml-1">{t.font_family.split(',')[0]!.replace(/'/g, '')}</span>
                  <span>·</span>
                  <span className="capitalize">{t.layout}</span>
                </div>
                <div className="mt-3 flex gap-2" onClick={(e) => e.stopPropagation()}>
                  <Button size="sm" variant="secondary" icon={<Pencil className="h-3.5 w-3.5" />} onClick={() => setForm({ template: t })}>
                    Edit
                  </Button>
                  {!t.is_active && (
                    <Button
                      size="sm"
                      variant="secondary"
                      icon={<CheckCircle2 className="h-3.5 w-3.5" />}
                      loading={activate.isPending && activate.variables === t.id}
                      onClick={() => doActivate(t)}
                    >
                      Activate
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>

          <Card
            className="xl:col-span-3"
            title={selectedTemplate ? `Preview: ${selectedTemplate.name}` : 'Preview'}
            actions={<EmployeePicker value={employeeId} onChange={setEmployeeId} hideLabel label="Preview employee" className="w-64 max-w-full" />}
          >
            <SignaturePreview
              html={signature.data?.html}
              loading={signature.isLoading && employeeId !== null}
              error={signature.isError ? friendlyError(signature.error, 'Unable to generate the signature.') : null}
              onRetry={() => signature.refetch()}
            />
          </Card>
        </div>
      )}

      {form && <TemplateFormDialog template={form.template} onClose={() => setForm(null)} />}
    </>
  )
}
