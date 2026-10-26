import { Navigate, Route, Routes } from 'react-router'
import { LoadingState } from '../components/ui/States'
import { homePathFor, useAuth } from '../hooks/useAuth'
import { AppShell } from '../layouts/AppShell'
import { AuditPage } from '../pages/admin/AuditPage'
import { BannersPage } from '../pages/admin/BannersPage'
import { EmployeeDetailPage } from '../pages/admin/EmployeeDetailPage'
import { EmployeesPage } from '../pages/admin/EmployeesPage'
import { OverviewPage } from '../pages/admin/OverviewPage'
import { SettingsPage } from '../pages/admin/SettingsPage'
import { SignaturesPage } from '../pages/admin/SignaturesPage'
import { TemplatesPage } from '../pages/admin/TemplatesPage'
import { MyProfilePage } from '../pages/employee/MyProfilePage'
import { MySignaturePage } from '../pages/employee/MySignaturePage'
import { LoginPage } from '../pages/LoginPage'
import { NotFoundPage } from '../pages/NotFoundPage'
import { ProtectedRoute } from './ProtectedRoute'

function HomeRedirect() {
  const { status, user } = useAuth()
  if (status === 'loading') return <LoadingState className="min-h-screen" />
  return <Navigate to={homePathFor(user)} replace />
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<HomeRedirect />} />
      <Route path="/login" element={<LoginPage />} />

      <Route
        path="/admin"
        element={
          <ProtectedRoute role="ADMIN">
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="overview" replace />} />
        <Route path="overview" element={<OverviewPage />} />
        <Route path="employees" element={<EmployeesPage />} />
        <Route path="employees/:id" element={<EmployeeDetailPage />} />
        <Route path="banners" element={<BannersPage />} />
        <Route path="signatures" element={<SignaturesPage />} />
        <Route path="templates" element={<TemplatesPage />} />
        <Route path="audit" element={<AuditPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>

      <Route
        path="/employee"
        element={
          <ProtectedRoute role="EMPLOYEE">
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="signature" replace />} />
        <Route path="signature" element={<MySignaturePage />} />
        <Route path="profile" element={<MyProfilePage />} />
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
