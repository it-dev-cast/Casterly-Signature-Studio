import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router'
import { LoadingState } from '../components/ui/States'
import { homePathFor, useAuth } from '../hooks/useAuth'
import type { Role } from '../types/api'

/**
 * Redirects anonymous users to /login and users with the wrong role to their own home.
 * (The backend enforces the same rules - this only keeps the UI consistent.)
 */
export function ProtectedRoute({ role, children }: { role: Role; children: ReactNode }) {
  const { status, user } = useAuth()
  const location = useLocation()

  if (status === 'loading') return <LoadingState label="Loading your workspace..." className="min-h-screen" />
  if (status === 'anonymous' || !user) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  if (user.role !== role) return <Navigate to={homePathFor(user)} replace />
  return <>{children}</>
}
