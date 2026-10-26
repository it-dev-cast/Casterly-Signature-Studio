import { ButtonLink } from '../components/ui/Button'
import { homePathFor, useAuth } from '../hooks/useAuth'

export function NotFoundPage() {
  const { user } = useAuth()
  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-6 text-center">
      <p className="text-sm font-semibold text-brand-600">404</p>
      <h1 className="mt-2 text-2xl font-semibold text-slate-900">Page not found</h1>
      <p className="mt-2 text-sm text-slate-500">The page you are looking for doesn’t exist or has moved.</p>
      <ButtonLink to={homePathFor(user)} variant="primary" className="mt-6">
        {user ? 'Back to dashboard' : 'Go to login'}
      </ButtonLink>
    </div>
  )
}
