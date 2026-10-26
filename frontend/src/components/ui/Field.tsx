import { useId, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from 'react'

const control =
  'block w-full rounded-lg border bg-surface px-3 text-sm text-slate-900 shadow-sm placeholder:text-slate-400 ' +
  'focus:outline-none focus:ring-2 disabled:bg-slate-50 disabled:text-slate-500'

const stateCls = (error?: string) =>
  error ? 'border-red-400 focus:border-red-500 focus:ring-red-500/20' : 'border-slate-300 focus:border-brand-500 focus:ring-brand-500/20'

interface FieldShellProps {
  label: string
  error?: string
  hint?: ReactNode
  required?: boolean
  className?: string
  children: (id: string, describedBy: string | undefined) => ReactNode
}

function FieldShell({ label, error, hint, required, className = '', children }: FieldShellProps) {
  const id = useId()
  const describedBy = error ? `${id}-error` : hint ? `${id}-hint` : undefined
  return (
    <div className={className}>
      <label htmlFor={id} className="mb-1.5 block text-sm font-medium text-slate-700">
        {label}
        {required && <span className="ml-0.5 text-red-500" aria-hidden="true">*</span>}
      </label>
      {children(id, describedBy)}
      {error ? (
        <p id={`${id}-error`} className="mt-1.5 text-xs text-red-600">
          {error}
        </p>
      ) : hint ? (
        <p id={`${id}-hint`} className="mt-1.5 text-xs text-slate-500">
          {hint}
        </p>
      ) : null}
    </div>
  )
}

interface TextFieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'onChange'> {
  label: string
  value: string
  onChange: (value: string) => void
  error?: string
  hint?: ReactNode
  containerClassName?: string
}

export function TextField({ label, value, onChange, error, hint, required, containerClassName, className = '', ...rest }: TextFieldProps) {
  return (
    <FieldShell label={label} error={error} hint={hint} required={required} className={containerClassName}>
      {(id, describedBy) => (
        <input
          id={id}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          aria-invalid={!!error || undefined}
          aria-describedby={describedBy}
          required={required}
          autoComplete="off"
          className={`${control} h-10 ${stateCls(error)} ${className}`}
          {...rest}
        />
      )}
    </FieldShell>
  )
}

interface TextAreaFieldProps extends Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, 'onChange'> {
  label: string
  value: string
  onChange: (value: string) => void
  error?: string
  hint?: ReactNode
  containerClassName?: string
}

export function TextAreaField({ label, value, onChange, error, hint, required, containerClassName, rows = 3, ...rest }: TextAreaFieldProps) {
  return (
    <FieldShell label={label} error={error} hint={hint} required={required} className={containerClassName}>
      {(id, describedBy) => (
        <textarea
          id={id}
          rows={rows}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          aria-invalid={!!error || undefined}
          aria-describedby={describedBy}
          autoComplete="off"
          className={`${control} py-2 ${stateCls(error)}`}
          {...rest}
        />
      )}
    </FieldShell>
  )
}

interface SelectFieldProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, 'onChange'> {
  label: string
  value: string
  onChange: (value: string) => void
  options: { value: string; label: string }[]
  error?: string
  hint?: ReactNode
  containerClassName?: string
  hideLabel?: boolean
}

export function SelectField({ label, value, onChange, options, error, hint, required, containerClassName, hideLabel, ...rest }: SelectFieldProps) {
  const select = (id: string, describedBy?: string) => (
    <select
      id={id}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      aria-invalid={!!error || undefined}
      aria-describedby={describedBy}
      aria-label={hideLabel ? label : undefined}
      className={`${control} h-10 pr-8 ${stateCls(error)}`}
      {...rest}
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  )
  if (hideLabel) return <div className={containerClassName}>{select(`${label}-select`)}</div>
  return (
    <FieldShell label={label} error={error} hint={hint} required={required} className={containerClassName}>
      {(id, describedBy) => select(id, describedBy)}
    </FieldShell>
  )
}

interface ToggleProps {
  label: string
  description?: string
  checked: boolean
  onChange: (checked: boolean) => void
  disabled?: boolean
}

export function Toggle({ label, description, checked, onChange, disabled }: ToggleProps) {
  return (
    <label className="flex cursor-pointer items-start gap-3">
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={label}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={`relative mt-0.5 inline-flex h-5 w-9 shrink-0 rounded-full transition-colors disabled:opacity-50 ${checked ? 'bg-brand-600' : 'bg-slate-300'}`}
      >
        <span className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform ${checked ? 'translate-x-4' : 'translate-x-0.5'}`} />
      </button>
      <span>
        <span className="block text-sm font-medium text-slate-700">{label}</span>
        {description && <span className="block text-xs text-slate-500">{description}</span>}
      </span>
    </label>
  )
}

export function FormSection({ title, description, children }: { title: string; description?: string; children: ReactNode }) {
  return (
    <fieldset className="space-y-4">
      <div>
        <legend className="text-sm font-semibold text-slate-900">{title}</legend>
        {description && <p className="mt-0.5 text-xs text-slate-500">{description}</p>}
      </div>
      {children}
    </fieldset>
  )
}
