import { useState, type FormEvent } from 'react'
import { useEmployeeMutations } from '../../hooks/queries'
import { NEXUS_SYNCED_FIELDS, type Employee, type EmployeeInput } from '../../types/api'
import { fieldErrors, friendlyError } from '../../utils/errors'
import { isEmail, isHttpUrl, isImageRef, isPhone, isWebsite, orNull } from '../../utils/validation'
import { ImageUpload } from '../common/ImageUpload'
import { assetUrl } from '../../utils/format'
import { Button } from '../ui/Button'
import { FormSection, TextAreaField, TextField, Toggle } from '../ui/Field'
import { Modal } from '../ui/Modal'
import { Alert } from '../ui/States'
import { useToast } from '../ui/Toast'

type Values = Record<
  | 'employee_code' | 'first_name' | 'last_name' | 'display_name' | 'designation' | 'department' | 'company'
  | 'email' | 'phone' | 'mobile' | 'website' | 'profile_photo_url' | 'linkedin_url' | 'twitter_url'
  | 'instagram_url' | 'other_social_url' | 'password',
  string
> & { is_active: boolean }

function initialValues(e?: Employee | null): Values {
  return {
    employee_code: e?.employee_code ?? '',
    first_name: e?.first_name ?? '',
    last_name: e?.last_name ?? '',
    display_name: e?.display_name ?? '',
    designation: e?.designation ?? '',
    department: e?.department ?? '',
    company: e?.company ?? '',
    email: e?.email ?? '',
    phone: e?.phone ?? '',
    mobile: e?.mobile ?? '',
    website: e?.website ?? '',
    profile_photo_url: e?.profile_photo_url ?? '',
    linkedin_url: e?.linkedin_url ?? '',
    twitter_url: e?.twitter_url ?? '',
    instagram_url: e?.instagram_url ?? '',
    other_social_url: e?.other_social_url ?? '',
    password: '',
    is_active: e?.is_active ?? true,
  }
}

export function validateEmployee(v: Values): Record<string, string> {
  const errors: Record<string, string> = {}
  const req = (k: keyof Values, label: string) => {
    if (!String(v[k]).trim()) errors[k] = `${label} is required.`
  }
  req('employee_code', 'Employee ID')
  req('first_name', 'First name')
  req('designation', 'Designation')
  req('email', 'Email')
  if (v.employee_code && !/^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$/.test(v.employee_code.trim()))
    errors.employee_code = "Use letters, numbers, '-' and '_' only."
  if (v.email && !isEmail(v.email)) errors.email = 'Enter a valid email address.'
  if (v.phone && !isPhone(v.phone)) errors.phone = 'Enter a valid phone number.'
  if (v.mobile && !isPhone(v.mobile)) errors.mobile = 'Enter a valid phone number.'
  if (v.website && !isWebsite(v.website)) errors.website = 'Enter a valid website.'
  if (v.profile_photo_url && !isImageRef(v.profile_photo_url)) errors.profile_photo_url = 'Upload a photo or enter a valid image URL.'
  for (const k of ['linkedin_url', 'twitter_url', 'instagram_url', 'other_social_url'] as const) {
    if (v[k] && !isHttpUrl(v[k])) errors[k] = 'Enter a full URL starting with https://'
  }
  if (v.password && v.password.length < 8) errors.password = 'Password must be at least 8 characters.'
  return errors
}

function toInput(v: Values): EmployeeInput {
  return {
    employee_code: v.employee_code.trim(),
    first_name: v.first_name.trim(),
    last_name: v.last_name.trim(),
    display_name: orNull(v.display_name),
    designation: v.designation.trim(),
    department: orNull(v.department),
    company: orNull(v.company),
    email: v.email.trim(),
    phone: orNull(v.phone),
    mobile: orNull(v.mobile),
    website: orNull(v.website),
    profile_photo_url: orNull(v.profile_photo_url),
    linkedin_url: orNull(v.linkedin_url),
    twitter_url: orNull(v.twitter_url),
    instagram_url: orNull(v.instagram_url),
    other_social_url: orNull(v.other_social_url),
    is_active: v.is_active,
    password: v.password ? v.password : null,
  }
}

interface Props {
  employee?: Employee | null
  onClose: () => void
  onSaved?: (employee: Employee) => void
}

/** Render only while open; state resets on every open. */
export function EmployeeFormDialog({ employee, onClose, onSaved }: Props) {
  const isEdit = !!employee
  const toast = useToast()
  const { create, update } = useEmployeeMutations()
  const [values, setValues] = useState<Values>(() => initialValues(employee))
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [formError, setFormError] = useState<string | null>(null)
  const saving = create.isPending || update.isPending

  const set = <K extends keyof Values>(key: K) => (value: Values[K]) => {
    setValues((v) => ({ ...v, [key]: value }))
    if (errors[key]) setErrors(({ [key]: _, ...rest }) => rest)
  }

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (saving) return
    const found = validateEmployee(values)
    setErrors(found)
    setFormError(null)
    if (Object.keys(found).length) return
    try {
      const input = toInput(values)
      const saved = isEdit ? await update.mutateAsync({ id: employee!.id, data: input }) : await create.mutateAsync(input)
      toast.success(isEdit ? 'Employee updated.' : 'Employee created.')
      onSaved?.(saved)
      onClose()
    } catch (err) {
      setErrors(fieldErrors(err))
      setFormError(friendlyError(err, isEdit ? 'Employee could not be updated.' : 'Employee could not be created.'))
    }
  }

  // A nexusAuth employee's synced fields are read-only here; they are edited in nexusAuth.
  const fromNexus = !!employee?.managed_by_nexus
  const locked = (key: string) => fromNexus && (NEXUS_SYNCED_FIELDS as readonly string[]).includes(key)
  // Photos copied from nexusAuth are stored as /uploads/photos/nexus-... (see backend nexus_sync.py).
  const photoFromNexus = fromNexus && values.profile_photo_url.startsWith('/uploads/photos/nexus-')
  const field = (key: keyof Omit<Values, 'is_active'>, label: string, extra: Record<string, unknown> = {}) => (
    <TextField
      label={label}
      value={values[key]}
      onChange={set(key)}
      error={errors[key]}
      {...extra}
      {...(locked(key) ? { disabled: true, required: false, hint: 'From nexusAuth' } : {})}
    />
  )

  return (
    <Modal
      open
      onClose={onClose}
      locked={saving}
      size="lg"
      title={isEdit ? `Edit ${employee!.full_name}` : 'Add employee'}
      description="Personal details used in this employee's email signature. The company banner is applied automatically."
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button type="submit" form="employee-form" loading={saving}>
            {isEdit ? 'Save changes' : 'Create employee'}
          </Button>
        </>
      }
    >
      <form autoComplete="off" id="employee-form" onSubmit={submit} noValidate className="space-y-8">
        {formError && <Alert>{formError}</Alert>}
        {fromNexus && (
          <Alert tone="info">
            This employee comes from nexusAuth. Name, Employee ID, designation, department, company, email, phone,
            LinkedIn, address and status are edited in nexusAuth and update here automatically. You can still set the
            signature-only details below.
          </Alert>
        )}

        <FormSection title="Identity">
          <div className="grid gap-4 sm:grid-cols-2">
            {field('employee_code', 'Employee ID', { required: true, placeholder: 'EMP-101' })}
            {field('display_name', 'Display name', { hint: 'Optional. Defaults to first + last name.' })}
            {field('first_name', 'First name', { required: true, autoComplete: 'off' })}
            {field('last_name', 'Last name', { autoComplete: 'off' })}
          </div>
        </FormSection>

        <FormSection title="Role">
          <div className="grid gap-4 sm:grid-cols-3">
            {field('designation', 'Designation', { required: true })}
            {field('department', 'Department')}
            {field('company', 'Company', { hint: 'Defaults to the company name in Settings.' })}
          </div>
        </FormSection>

        <FormSection title="Contact">
          <div className="grid gap-4 sm:grid-cols-2">
            {field('email', 'Email', { required: true, type: 'email', autoComplete: 'off' })}
            {field('website', 'Website', { placeholder: 'www.example.com' })}
            {field('phone', 'Phone', { type: 'tel', placeholder: '+1 555 010 2000' })}
            {field('mobile', 'Mobile', { type: 'tel' })}
            {/* The address comes only from nexusAuth (employee sync); it is shown here, never edited. */}
            <TextAreaField
              label="Address"
              value={employee?.address ?? ''}
              onChange={() => {}}
              rows={2}
              disabled
              placeholder="Not set in nexusAuth"
              hint="From nexusAuth. Add or change it in nexusAuth; it updates here automatically."
              containerClassName="sm:col-span-2"
            />
          </div>
        </FormSection>

        <FormSection title="Profile photo">
          {photoFromNexus ? (
            <div className="flex items-center gap-4">
              <img src={assetUrl(values.profile_photo_url) ?? undefined} alt="" className="h-16 w-16 rounded-full object-cover" />
              <p className="text-sm text-slate-500">From nexusAuth. Change or remove the photo in nexusAuth; it updates here automatically.</p>
            </div>
          ) : (
            <ImageUpload
              label="Photo"
              kind="photo"
              value={values.profile_photo_url}
              onChange={set('profile_photo_url')}
              error={errors.profile_photo_url}
              hint={fromNexus ? 'A photo added in nexusAuth replaces this one.' : 'Square images work best (at least 176 × 176 px).'}
            />
          )}
        </FormSection>

        <FormSection title="Social links" description="All optional. Use full URLs.">
          <div className="grid gap-4 sm:grid-cols-2">
            {field('linkedin_url', 'LinkedIn', { placeholder: 'https://www.linkedin.com/in/…' })}
            {field('twitter_url', 'X / Twitter', { placeholder: 'https://x.com/…' })}
            {field('instagram_url', 'Instagram', { placeholder: 'https://instagram.com/…' })}
            {field('other_social_url', 'Other link', { placeholder: 'https://…' })}
          </div>
        </FormSection>

        <FormSection title="Account">
          <Toggle
            label="Active"
            description="Inactive employees cannot sign in."
            checked={values.is_active}
            onChange={set('is_active')}
            disabled={fromNexus}
          />
          {field('password', employee?.has_login ? 'Reset password' : 'Login password', {
            type: 'password',
            autoComplete: 'new-password',
            hint: employee?.has_login
              ? 'Leave blank to keep the current password.'
              : 'Optional. Set a password to let this employee sign in and view their signature.',
          })}
        </FormSection>
      </form>
    </Modal>
  )
}
