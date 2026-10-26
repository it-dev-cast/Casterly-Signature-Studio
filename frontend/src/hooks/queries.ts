/**
 * React Query hooks. Every mutation invalidates the affected queries so the UI
 * always reflects real backend state (no optimistic/fake local state).
 */
import { keepPreviousData, useMutation, useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query'
import {
  auditApi,
  bannersApi,
  employeesApi,
  integrationsApi,
  overviewApi,
  settingsApi,
  signaturesApi,
  templatesApi,
  type AuditParams,
  type EmployeeListParams,
} from '../services/api'
import type { AppSettingsInput, BannerInput, BannerStatus, EmployeeInput, TemplateInput } from '../types/api'

export const keys = {
  overview: ['overview'] as const,
  nexusStatus: ['nexusStatus'] as const,
  employees: (p: EmployeeListParams) => ['employees', p] as const,
  employee: (id: number) => ['employee', id] as const,
  departments: ['departments'] as const,
  myProfile: ['myProfile'] as const,
  banners: (status?: BannerStatus) => ['banners', status ?? 'all'] as const,
  banner: (id: number) => ['banner', id] as const,
  currentBanner: ['currentBanner'] as const,
  signature: (employeeId: number, templateId?: number) => ['signature', employeeId, templateId ?? null] as const,
  mySignature: ['mySignature'] as const,
  templates: ['templates'] as const,
  layouts: ['layouts'] as const,
  audit: (p: AuditParams) => ['audit', p] as const,
  settings: ['settings'] as const,
  branding: ['branding'] as const,
}

function invalidate(qc: QueryClient, ...roots: string[]) {
  return Promise.all(roots.map((root) => qc.invalidateQueries({ queryKey: [root] })))
}

// Anything that changes a banner can change every signature and the overview.
const BANNER_ROOTS = ['banners', 'banner', 'currentBanner', 'overview', 'signature', 'mySignature', 'audit']
const EMPLOYEE_ROOTS = ['employees', 'employee', 'departments', 'overview', 'signature', 'audit']
const TEMPLATE_ROOTS = ['templates', 'overview', 'signature', 'mySignature', 'audit']

// ---------------------------------------------------------------- queries --
export const useOverview = () => useQuery({ queryKey: keys.overview, queryFn: overviewApi.get })

export const useEmployees = (params: EmployeeListParams) =>
  useQuery({ queryKey: keys.employees(params), queryFn: () => employeesApi.list(params), placeholderData: keepPreviousData })

export const useEmployee = (id: number) =>
  useQuery({ queryKey: keys.employee(id), queryFn: () => employeesApi.get(id), enabled: Number.isFinite(id) })

export const useDepartments = () => useQuery({ queryKey: keys.departments, queryFn: employeesApi.departments })

export const useMyProfile = () => useQuery({ queryKey: keys.myProfile, queryFn: employeesApi.me })

export const useBanners = (status?: BannerStatus) =>
  useQuery({ queryKey: keys.banners(status), queryFn: () => bannersApi.list(status) })

export const useBanner = (id: number | null) =>
  useQuery({ queryKey: keys.banner(id ?? -1), queryFn: () => bannersApi.get(id!), enabled: id !== null })

export const useCurrentBanner = () => useQuery({ queryKey: keys.currentBanner, queryFn: bannersApi.current })

export const useSignature = (employeeId: number | null, templateId?: number) =>
  useQuery({
    queryKey: keys.signature(employeeId ?? -1, templateId),
    queryFn: () => signaturesApi.get(employeeId!, templateId),
    enabled: employeeId !== null,
  })

export const useOutlookStatus = (employeeId: number | null) =>
  useQuery({
    queryKey: ['outlookStatus', employeeId ?? -1],
    queryFn: () => signaturesApi.outlookStatus(employeeId!),
    enabled: employeeId !== null,
    refetchInterval: 30_000,  // the add-in reports each time the employee writes an email
  })

export const useMySignature = () => useQuery({ queryKey: keys.mySignature, queryFn: signaturesApi.mine })

export const useTemplates = () => useQuery({ queryKey: keys.templates, queryFn: templatesApi.list })

export const useLayouts = () => useQuery({ queryKey: keys.layouts, queryFn: templatesApi.layouts, staleTime: Infinity })

export const useAuditLogs = (params: AuditParams) =>
  useQuery({ queryKey: keys.audit(params), queryFn: () => auditApi.list(params), placeholderData: keepPreviousData })

export const useSettings = () => useQuery({ queryKey: keys.settings, queryFn: settingsApi.get })

/** Public company name + logo (login page and app header). */
export const useBranding = () =>
  useQuery({ queryKey: keys.branding, queryFn: settingsApi.branding, staleTime: 5 * 60_000 })

// -------------------------------------------------------------- mutations --
/** nexusAuth sync status, polled so the Employees page shows changes made in nexusAuth. */
export function useNexusSync() {
  const qc = useQueryClient()
  const status = useQuery({
    queryKey: keys.nexusStatus,
    queryFn: integrationsApi.nexusStatus,
    refetchInterval: (query) => (query.state.data?.enabled ? 10_000 : false),
  })
  const syncNow = useMutation({
    mutationFn: integrationsApi.nexusSync,
    onSuccess: (data) => {
      qc.setQueryData(keys.nexusStatus, data)
      return invalidate(qc, ...EMPLOYEE_ROOTS)
    },
  })
  return { status, syncNow, refreshEmployees: () => invalidate(qc, ...EMPLOYEE_ROOTS) }
}

export function useEmployeeMutations() {
  const qc = useQueryClient()
  const done = () => invalidate(qc, ...EMPLOYEE_ROOTS)
  return {
    create: useMutation({ mutationFn: (d: EmployeeInput) => employeesApi.create(d), onSuccess: done }),
    update: useMutation({
      mutationFn: ({ id, data }: { id: number; data: EmployeeInput }) => employeesApi.update(id, data),
      onSuccess: done,
    }),
    setStatus: useMutation({
      mutationFn: ({ id, active }: { id: number; active: boolean }) => employeesApi.setStatus(id, active),
      onSuccess: done,
    }),
    remove: useMutation({ mutationFn: (id: number) => employeesApi.remove(id), onSuccess: done }),
  }
}

export function useBannerMutations() {
  const qc = useQueryClient()
  const done = () => invalidate(qc, ...BANNER_ROOTS)
  return {
    create: useMutation({ mutationFn: (d: BannerInput) => bannersApi.create(d), onSuccess: done }),
    update: useMutation({
      mutationFn: ({ id, data }: { id: number; data: BannerInput }) => bannersApi.update(id, data),
      onSuccess: done,
    }),
    publish: useMutation({ mutationFn: (id: number) => bannersApi.publish(id), onSuccess: done }),
    unpublish: useMutation({ mutationFn: (id: number) => bannersApi.unpublish(id), onSuccess: done }),
    archive: useMutation({ mutationFn: (id: number) => bannersApi.archive(id), onSuccess: done }),
    remove: useMutation({ mutationFn: (id: number) => bannersApi.remove(id), onSuccess: done }),
  }
}

export function useTemplateMutations() {
  const qc = useQueryClient()
  const done = () => invalidate(qc, ...TEMPLATE_ROOTS)
  return {
    create: useMutation({ mutationFn: (d: TemplateInput) => templatesApi.create(d), onSuccess: done }),
    update: useMutation({
      mutationFn: ({ id, data }: { id: number; data: TemplateInput }) => templatesApi.update(id, data),
      onSuccess: done,
    }),
    activate: useMutation({ mutationFn: (id: number) => templatesApi.activate(id), onSuccess: done }),
  }
}

export function useSettingsMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (d: AppSettingsInput) => settingsApi.update(d),
    onSuccess: () => invalidate(qc, 'settings', 'branding', 'signature', 'mySignature', 'audit', 'outlookStatus'),
  })
}
