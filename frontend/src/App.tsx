import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState, type ReactNode } from 'react'
import { BrowserRouter } from 'react-router'
import { ToastProvider } from './components/ui/Toast'
import { AuthProvider } from './hooks/useAuth'
import { AppRoutes } from './routes/AppRoutes'
import { ApiError } from './services/http'

// Vite's `base` (e.g. '/signature/' when served under a sub-path); '/' by default.
const ROUTER_BASENAME = import.meta.env.BASE_URL.replace(/\/+$/, '') || '/'

export function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        refetchOnWindowFocus: false,
        // Retry once on network/server errors only - never on 4xx.
        retry: (count, error) => count < 1 && (!(error instanceof ApiError) || error.status === 0 || error.status >= 500),
      },
    },
  })
}

/** Providers shared by the app and the tests. */
export function AppProviders({ children, client }: { children: ReactNode; client?: QueryClient }) {
  const [queryClient] = useState(() => client ?? createQueryClient())
  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <AuthProvider>{children}</AuthProvider>
      </ToastProvider>
    </QueryClientProvider>
  )
}

export default function App() {
  return (
    <BrowserRouter basename={ROUTER_BASENAME}>
      <AppProviders>
        <AppRoutes />
      </AppProviders>
    </BrowserRouter>
  )
}
