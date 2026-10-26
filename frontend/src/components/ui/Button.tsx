import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { Link, type LinkProps } from 'react-router'
import { Spinner } from './Spinner'

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost'
type Size = 'sm' | 'md'

const base =
  'inline-flex items-center justify-center gap-2 rounded-lg font-medium whitespace-nowrap transition-colors ' +
  'disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline-2 focus-visible:outline-offset-2'

const variants: Record<Variant, string> = {
  primary: 'bg-brand-600 text-white shadow-sm hover:bg-brand-hover focus-visible:outline-brand-600',
  secondary: 'bg-surface text-slate-700 border border-slate-300 shadow-sm hover:bg-slate-50 focus-visible:outline-brand-600',
  danger: 'bg-red-600 text-white shadow-sm hover:bg-danger-hover focus-visible:outline-red-600',
  ghost: 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 focus-visible:outline-brand-600',
}

const sizes: Record<Size, string> = {
  sm: 'h-8 px-3 text-sm',
  md: 'h-10 px-4 text-sm',
}

export function buttonClasses(variant: Variant = 'primary', size: Size = 'md', extra = '') {
  return `${base} ${variants[variant]} ${sizes[size]} ${extra}`
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  loading?: boolean
  icon?: ReactNode
}

export function Button({ variant = 'primary', size = 'md', loading, icon, disabled, className = '', children, type = 'button', ...rest }: ButtonProps) {
  return (
    <button
      type={type}
      className={buttonClasses(variant, size, className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading ? <Spinner className="h-4 w-4" /> : icon}
      {children}
    </button>
  )
}

interface ButtonLinkProps extends LinkProps {
  variant?: Variant
  size?: Size
  icon?: ReactNode
}

export function ButtonLink({ variant = 'secondary', size = 'md', icon, className = '', children, ...rest }: ButtonLinkProps) {
  return (
    <Link className={buttonClasses(variant, size, className)} {...rest}>
      {icon}
      {children}
    </Link>
  )
}

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  label: string
  tone?: 'default' | 'danger'
}

export function IconButton({ label, tone = 'default', className = '', children, type = 'button', ...rest }: IconButtonProps) {
  const color = tone === 'danger' ? 'text-slate-500 hover:bg-red-50 hover:text-red-600' : 'text-slate-500 hover:bg-slate-100 hover:text-slate-900'
  return (
    <button
      type={type}
      aria-label={label}
      title={label}
      className={`inline-flex h-8 w-8 items-center justify-center rounded-md transition-colors disabled:opacity-50 ${color} ${className}`}
      {...rest}
    >
      {children}
    </button>
  )
}
