import { useQueryClient } from '@tanstack/react-query'
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { authApi } from '../services/api'
import { setUnauthorizedHandler } from '../services/http'
import { tokenStorage } from '../services/tokenStorage'
import type { Employee, User } from '../types/api'

type Status = 'loading' | 'authenticated' | 'anonymous'

interface AuthContextValue {
  status: Status
  user: User | null
  employee: Employee | null
  /** Message to show on the login page, e.g. after the session expired. */
  notice: string | null
  login: (email: string, password: string, remember: boolean) => Promise<User>
  logout: () => Promise<void>
  clearNotice: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [status, setStatus] = useState<Status>(() => (tokenStorage.get() ? 'loading' : 'anonymous'))
  const [user, setUser] = useState<User | null>(null)
  const [employee, setEmployee] = useState<Employee | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const endSession = useCallback(
    (message: string | null) => {
      tokenStorage.clear()
      setUser(null)
      setEmployee(null)
      setStatus('anonymous')
      setNotice(message)
      queryClient.clear()
    },
    [queryClient],
  )

  // Any 401 from the API (expired / revoked token) ends the session everywhere.
  useEffect(() => {
    setUnauthorizedHandler(() => endSession('Your session has expired. Please login again.'))
    return () => setUnauthorizedHandler(null)
  }, [endSession])

  // Restore an existing session on first load.
  useEffect(() => {
    if (!tokenStorage.get()) return
    let cancelled = false
    authApi
      .me()
      .then((me) => {
        if (cancelled) return
        setUser(me.user)
        setEmployee(me.employee)
        setStatus('authenticated')
      })
      .catch(() => {
        if (!cancelled) endSession(null)
      })
    return () => {
      cancelled = true
    }
  }, [endSession])

  const login = useCallback(async (email: string, password: string, remember: boolean) => {
    const res = await authApi.login(email, password, remember)
    tokenStorage.set(res.access_token, remember)
    setUser(res.user)
    setEmployee(res.employee)
    setNotice(null)
    setStatus('authenticated')
    return res.user
  }, [])

  const logout = useCallback(async () => {
    try {
      await authApi.logout()
    } catch {
      // The token is discarded locally regardless.
    }
    endSession(null)
  }, [endSession])

  const value = useMemo<AuthContextValue>(
    () => ({ status, user, employee, notice, login, logout, clearNotice: () => setNotice(null) }),
    [status, user, employee, notice, login, logout],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}

export function homePathFor(user: User | null): string {
  if (!user) return '/login'
  return user.role === 'ADMIN' ? '/admin/overview' : '/employee/signature'
}
