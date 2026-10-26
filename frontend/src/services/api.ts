import type {
  AppSettings,
  AppSettingsInput,
  AuditLog,
  Banner,
  BannerInput,
  BannerStatus,
  BannerWithHtml,
  Branding,
  Employee,
  EmployeeInput,
  LayoutInfo,
  LoginResponse,
  MeResponse,
  NexusSyncStatus,
  OutlookStatus,
  Overview,
  Page,
  Signature,
  SignatureTemplate,
  TemplateInput,
  UploadResult,
} from '../types/api'
import { request, requestFile } from './http'

export const authApi = {
  login: (email: string, password: string, remember_me: boolean) =>
    request<LoginResponse>('/api/auth/login', { method: 'POST', body: { email, password, remember_me } }),
  me: () => request<MeResponse>('/api/auth/me'),
  logout: () => request<{ message: string }>('/api/auth/logout', { method: 'POST' }),
}

export interface EmployeeListParams {
  q?: string
  department?: string
  status?: 'all' | 'active' | 'inactive'
  page?: number
  page_size?: number
}

export const employeesApi = {
  list: (params: EmployeeListParams = {}) =>
    request<Page<Employee>>('/api/employees', { query: { ...params } }),
  departments: () => request<string[]>('/api/employees/departments'),
  me: () => request<Employee>('/api/employees/me'),
  get: (id: number) => request<Employee>(`/api/employees/${id}`),
  create: (data: EmployeeInput) => request<Employee>('/api/employees', { method: 'POST', body: data }),
  update: (id: number, data: EmployeeInput) =>
    request<Employee>(`/api/employees/${id}`, { method: 'PUT', body: data }),
  setStatus: (id: number, is_active: boolean) =>
    request<Employee>(`/api/employees/${id}/status`, { method: 'PATCH', body: { is_active } }),
  remove: (id: number) => request<{ deleted: boolean }>(`/api/employees/${id}`, { method: 'DELETE' }),
}

export const bannersApi = {
  list: (status?: BannerStatus) => request<Banner[]>('/api/banners', { query: { status } }),
  current: () => request<{ banner: BannerWithHtml | null }>('/api/banners/current'),
  get: (id: number) => request<BannerWithHtml>(`/api/banners/${id}`),
  preview: (data: BannerInput) => request<{ html: string }>('/api/banners/preview', { method: 'POST', body: data }),
  create: (data: BannerInput) => request<BannerWithHtml>('/api/banners', { method: 'POST', body: data }),
  update: (id: number, data: BannerInput) =>
    request<BannerWithHtml>(`/api/banners/${id}`, { method: 'PUT', body: data }),
  publish: (id: number) => request<BannerWithHtml>(`/api/banners/${id}/publish`, { method: 'POST' }),
  unpublish: (id: number) => request<BannerWithHtml>(`/api/banners/${id}/unpublish`, { method: 'POST' }),
  archive: (id: number) => request<BannerWithHtml>(`/api/banners/${id}/archive`, { method: 'POST' }),
  remove: (id: number) => request<{ deleted: boolean }>(`/api/banners/${id}`, { method: 'DELETE' }),
}

export const signaturesApi = {
  get: (employeeId: number, templateId?: number) =>
    request<Signature>(`/api/signatures/${employeeId}`, { query: { template_id: templateId } }),
  mine: () => request<Signature>('/api/signatures/me'),
  downloadDocument: (employeeId: number, templateId?: number) =>
    request<string>(`/api/signatures/${employeeId}/html`, {
      query: { download: true, live: true, template_id: templateId },
      raw: true,
    }),
  /** Personal Windows installer that puts the signature into classic Outlook. */
  outlookInstaller: (employeeId: number) => requestFile(`/api/signatures/${employeeId}/installer`),
  /** Email the employee their signature + a personal setup link (admin only). */
  sendSetupEmail: (employeeId: number) =>
    request<Omit<SetupLink, 'email_html'> & { sent: boolean }>(`/api/signatures/${employeeId}/send-setup-email`, { method: 'POST' }),
  setupLink: (employeeId: number) => request<SetupLink>(`/api/signatures/${employeeId}/setup-link`),
  outlookStatus: (employeeId: number) => request<OutlookStatus>(`/api/signatures/${employeeId}/outlook-status`),
}

export interface SetupLink {
  employee_id: number
  email: string
  link: string
  subject: string
  email_configured: boolean
  /** Ready-made message (clickable button + signature) to paste into the mail app. */
  email_html: string
}

export const templatesApi = {
  list: () => request<SignatureTemplate[]>('/api/templates'),
  layouts: () => request<LayoutInfo[]>('/api/templates/layouts'),
  create: (data: TemplateInput) => request<SignatureTemplate>('/api/templates', { method: 'POST', body: data }),
  update: (id: number, data: TemplateInput) =>
    request<SignatureTemplate>(`/api/templates/${id}`, { method: 'PUT', body: data }),
  activate: (id: number) => request<SignatureTemplate>(`/api/templates/${id}/activate`, { method: 'POST' }),
}

export const integrationsApi = {
  nexusStatus: () => request<NexusSyncStatus>('/api/integrations/nexusauth'),
  nexusSync: () => request<NexusSyncStatus>('/api/integrations/nexusauth/sync', { method: 'POST' }),
}

export const overviewApi = {
  get: () => request<Overview>('/api/overview'),
}

export interface AuditParams {
  action?: string
  q?: string
  page?: number
  page_size?: number
}

export const auditApi = {
  list: (params: AuditParams = {}) => request<Page<AuditLog>>('/api/audit-logs', { query: { ...params } }),
}

export const settingsApi = {
  branding: () => request<Branding>('/api/branding'),
  get: () => request<AppSettings>('/api/settings'),
  update: (data: AppSettingsInput) => request<AppSettings>('/api/settings', { method: 'PUT', body: data }),
}

export type UploadKind = 'banner' | 'photo'

export const uploadsApi = {
  image: (file: File, kind: UploadKind) => {
    const form = new FormData()
    form.append('file', file)
    form.append('kind', kind)
    return request<UploadResult>('/api/uploads', { method: 'POST', formData: form })
  },
}
