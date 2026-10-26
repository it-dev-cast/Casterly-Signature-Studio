import { useEffect } from 'react'
import { useEmployees } from '../../hooks/queries'
import { SelectField } from '../ui/Field'

interface Props {
  value: number | null
  onChange: (id: number | null) => void
  label?: string
  hideLabel?: boolean
  className?: string
}

/** Select an employee; auto-selects the first one when nothing is chosen yet. */
export function EmployeePicker({ value, onChange, label = 'Employee', hideLabel, className }: Props) {
  const { data, isLoading } = useEmployees({ page_size: 200, status: 'all' })
  const items = data?.items ?? []

  useEffect(() => {
    if (value === null && items.length > 0) onChange(items[0]!.id)
  }, [value, items, onChange])

  const options = isLoading
    ? [{ value: '', label: 'Loading employees...' }]
    : items.length === 0
      ? [{ value: '', label: 'No employees yet' }]
      : items.map((e) => ({ value: String(e.id), label: `${e.full_name} — ${e.designation}${e.is_active ? '' : ' (inactive)'}` }))

  return (
    <SelectField
      label={label}
      hideLabel={hideLabel}
      containerClassName={className}
      value={value === null ? '' : String(value)}
      onChange={(v) => onChange(v ? Number(v) : null)}
      options={options}
      disabled={isLoading || items.length === 0}
    />
  )
}
