import { useState, type FormEvent } from 'react'
import { useLayouts, useTemplateMutations } from '../../hooks/queries'
import type { SignatureTemplate, TemplateInput } from '../../types/api'
import { fieldErrors, friendlyError } from '../../utils/errors'
import { isHexColor, orNull } from '../../utils/validation'
import { Button } from '../ui/Button'
import { SelectField, TextAreaField, TextField, Toggle } from '../ui/Field'
import { Modal } from '../ui/Modal'
import { Alert } from '../ui/States'
import { useToast } from '../ui/Toast'

const FONTS = [
  'Arial, Helvetica, sans-serif',
  'Verdana, Geneva, sans-serif',
  'Tahoma, Geneva, sans-serif',
  "'Trebuchet MS', Helvetica, sans-serif",
  'Georgia, serif',
  "'Times New Roman', Times, serif",
]

function ColorField({ label, value, onChange, error }: { label: string; value: string; onChange: (v: string) => void; error?: string }) {
  return (
    <div>
      <p className="mb-1.5 text-sm font-medium text-slate-700">{label}</p>
      <div className="flex items-center gap-2">
        <input
          type="color"
          aria-label={`${label} picker`}
          value={isHexColor(value) ? value : '#000000'}
          onChange={(e) => onChange(e.target.value.toUpperCase())}
          className="h-10 w-12 cursor-pointer rounded-md border border-slate-300 bg-surface p-1"
        />
        <TextField label={`${label} hex`} value={value} onChange={onChange} error={error} containerClassName="flex-1 [&>label]:sr-only" />
      </div>
    </div>
  )
}

export function TemplateFormDialog({ template, onClose }: { template?: SignatureTemplate | null; onClose: () => void }) {
  const toast = useToast()
  const layouts = useLayouts()
  const { create, update } = useTemplateMutations()
  const [values, setValues] = useState<TemplateInput>(() => ({
    name: template?.name ?? '',
    description: template?.description ?? '',
    layout: template?.layout ?? 'classic',
    primary_color: template?.primary_color ?? '#1F2A44',
    accent_color: template?.accent_color ?? '#2563EB',
    font_family: template?.font_family ?? FONTS[0]!,
    show_photo: template?.show_photo ?? true,
    show_social: template?.show_social ?? true,
  }))
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [formError, setFormError] = useState<string | null>(null)
  const saving = create.isPending || update.isPending

  const set = <K extends keyof TemplateInput>(key: K) => (value: TemplateInput[K]) => setValues((v) => ({ ...v, [key]: value }))

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (saving) return
    const found: Record<string, string> = {}
    if (!values.name.trim()) found.name = 'Template name is required.'
    if (!isHexColor(values.primary_color)) found.primary_color = 'Use a hex colour like #1F2A44.'
    if (!isHexColor(values.accent_color)) found.accent_color = 'Use a hex colour like #2563EB.'
    setErrors(found)
    setFormError(null)
    if (Object.keys(found).length) return
    const data = { ...values, name: values.name.trim(), description: orNull(values.description ?? '') }
    try {
      if (template) await update.mutateAsync({ id: template.id, data })
      else await create.mutateAsync(data)
      toast.success(template ? 'Template updated.' : 'Template created.')
      onClose()
    } catch (err) {
      setErrors(fieldErrors(err))
      setFormError(friendlyError(err, 'The template could not be saved.'))
    }
  }

  const fontOptions = FONTS.includes(values.font_family) ? FONTS : [values.font_family, ...FONTS]

  return (
    <Modal
      open
      onClose={onClose}
      locked={saving}
      title={template ? `Edit ${template.name}` : 'New signature template'}
      description="Templates control the signature layout and styling. Employee data and the current banner are filled in automatically."
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button type="submit" form="template-form" loading={saving}>
            {template ? 'Save changes' : 'Create template'}
          </Button>
        </>
      }
    >
      <form autoComplete="off" id="template-form" onSubmit={submit} noValidate className="space-y-5">
        {formError && <Alert>{formError}</Alert>}
        <TextField label="Name" required value={values.name} onChange={set('name')} error={errors.name} />
        <TextAreaField label="Description" value={values.description ?? ''} onChange={set('description')} rows={2} />
        <SelectField
          label="Layout"
          value={values.layout}
          onChange={set('layout')}
          error={errors.layout}
          options={(layouts.data ?? [{ key: 'classic', name: 'Classic', description: '' }]).map((l) => ({
            value: l.key,
            label: l.description ? `${l.name} — ${l.description}` : l.name,
          }))}
        />
        <div className="grid gap-4 sm:grid-cols-2">
          <ColorField label="Primary colour" value={values.primary_color} onChange={set('primary_color')} error={errors.primary_color} />
          <ColorField label="Accent colour" value={values.accent_color} onChange={set('accent_color')} error={errors.accent_color} />
        </div>
        <SelectField
          label="Font"
          value={values.font_family}
          onChange={set('font_family')}
          hint="Email-safe fonts only, so signatures look the same in every client."
          options={fontOptions.map((f) => ({ value: f, label: f.split(',')[0]!.replace(/'/g, '') }))}
        />
        <div className="grid gap-4 sm:grid-cols-2">
          <Toggle label="Show profile photo" checked={values.show_photo} onChange={set('show_photo')} />
          <Toggle label="Show social links" checked={values.show_social} onChange={set('show_social')} />
        </div>
      </form>
    </Modal>
  )
}
