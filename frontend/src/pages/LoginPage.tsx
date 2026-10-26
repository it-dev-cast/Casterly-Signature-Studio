import { Eye, EyeOff } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router'
import { CompanyBrand } from '../components/common/CompanyBrand'
import { Button } from '../components/ui/Button'
import { TextField } from '../components/ui/Field'
import { Alert } from '../components/ui/States'
import { homePathFor, useAuth } from '../hooks/useAuth'
import { friendlyError } from '../utils/errors'
import { isEmail } from '../utils/validation'

export function LoginPage() {
  const { status, user, notice, login, clearNotice } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [remember, setRemember] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (status === 'authenticated' && user) return <Navigate to={homePathFor(user)} replace />

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (submitting) return
    clearNotice()
    if (!isEmail(email)) return setError('Enter a valid email address.')
    if (!password) return setError('Enter your password.')
    setError(null)
    setSubmitting(true)
    try {
      const signedIn = await login(email.trim(), password, remember)
      const from = (location.state as { from?: string } | null)?.from
      const home = homePathFor(signedIn)
      // Only return to a page the user is allowed to see.
      navigate(from && from.startsWith(home.split('/').slice(0, 2).join('/')) ? from : home, { replace: true })
    } catch (err) {
      setError(friendlyError(err, 'Unable to sign in. Please try again.'))
      setSubmitting(false)
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-slate-50 px-4 py-12">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center text-center">
          <CompanyBrand variant="login" />
          <h1 className="mt-5 text-xl font-semibold text-slate-900">Sign in to Signature Studio</h1>
          <p className="mt-1 text-sm text-slate-500">Manage company email signatures and banners.</p>
        </div>

        <form autoComplete="off" onSubmit={submit} noValidate className="relative space-y-5 overflow-hidden rounded-2xl border border-slate-200 bg-surface p-6 pt-7 shadow-sm">
          <span className="pointer-events-none absolute inset-x-0 top-0 h-[3px] bg-linear-to-r from-brand-600 via-brand-400 to-lime-accent" aria-hidden="true" />
          {notice && <Alert tone="warning">{notice}</Alert>}
          {error && <Alert>{error}</Alert>}
          <TextField label="Email" type="email" autoComplete="off" value={email} onChange={setEmail} required autoFocus />
          <div className="relative">
            <TextField
              label="Password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="current-password"
              value={password}
              onChange={setPassword}
              required
              className="pr-10"
            />
            <button
              type="button"
              onClick={() => setShowPassword((s) => !s)}
              className="absolute right-2 top-[34px] rounded p-1 text-slate-400 hover:text-slate-600"
              aria-label={showPassword ? 'Hide password' : 'Show password'}
            >
              {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <input
              type="checkbox"
              checked={remember}
              onChange={(e) => setRemember(e.target.checked)}
              className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
            />
            Remember me on this device
          </label>
          <Button type="submit" className="w-full" loading={submitting}>
            Sign in
          </Button>
        </form>
      </div>
    </div>
  )
}
