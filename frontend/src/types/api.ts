export type Role = 'ADMIN' | 'EMPLOYEE'

export type BannerStatus = 'DRAFT' | 'SCHEDULED' | 'PUBLISHED' | 'EXPIRED' | 'ARCHIVED'

export interface User {
  id: number
  email: string
  role: Role
  is_active: boolean
}

export interface Employee {
  id: number
  employee_code: string
  user_id: number | null
  first_name: string
  last_name: string
  display_name: string | null
  full_name: string
  designation: string
  department: string | null
  company: string | null
  email: string
  phone: string | null
  mobile: string | null
  website: string | null
  address: string | null
  profile_photo_url: string | null
  linkedin_url: string | null
  twitter_url: string | null
  instagram_url: string | null
  other_social_url: string | null
  is_active: boolean
  has_login: boolean
  /** Kept in sync from nexusAuth; the synced fields can only be changed there. */
  managed_by_nexus: boolean
  nexus_employee_id: number | null
  nexus_synced_at: string | null
  created_at: string
  updated_at: string
}

/** Employee fields owned by nexusAuth for a synced employee. */
export const NEXUS_SYNCED_FIELDS = [
  'employee_code', 'first_name', 'last_name', 'designation', 'department', 'company', 'email', 'phone',
  'linkedin_url', 'address', 'is_active',
] as const

export interface NexusSyncRun {
  started_at: string
  finished_at: string | null
  ok: boolean
  created: number
  updated: number
  deactivated: number
  unchanged: number
  total_remote: number
  error: string | null
  login_rejected: boolean
  problems: string[]
}

export interface NexusSyncStatus {
  enabled: boolean
  url: string | null
  interval_seconds: number
  synced_fields: string[]
  last_success_at: string | null
  paused: boolean
  last_run: NexusSyncRun | null
}

export interface EmployeeInput {
  employee_code: string
  first_name: string
  last_name: string
  display_name: string | null
  designation: string
  department: string | null
  company: string | null
  email: string
  phone: string | null
  mobile: string | null
  website: string | null
  profile_photo_url: string | null
  linkedin_url: string | null
  twitter_url: string | null
  instagram_url: string | null
  other_social_url: string | null
  is_active: boolean
  password?: string | null
}

export interface Banner {
  id: number
  name: string
  title: string
  description: string | null
  image_url: string
  image_public_url: string
  target_url: string | null
  status: BannerStatus
  effective_status: BannerStatus
  is_current: boolean
  start_date: string | null
  end_date: string | null
  published_at: string | null
  created_by: number | null
  created_by_email: string | null
  created_at: string
  updated_at: string
}

export interface BannerWithHtml extends Banner {
  html: string
}

export interface BannerInput {
  name: string
  title: string
  description: string | null
  image_url: string
  target_url: string | null
  start_date: string | null
  end_date: string | null
}

export interface SignatureTemplate {
  id: number
  name: string
  description: string | null
  layout: string
  primary_color: string
  accent_color: string
  font_family: string
  show_photo: boolean
  show_social: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

export type TemplateInput = Omit<SignatureTemplate, 'id' | 'is_active' | 'created_at' | 'updated_at'>

export interface LayoutInfo {
  key: string
  name: string
  description: string
}

export interface Signature {
  employee: Employee
  template: SignatureTemplate | null
  banner: BannerWithHtml | null
  /** Preview version: shows today's banner image directly. */
  html: string
  /** Copy/paste version: the banner always shows whatever is published. */
  live_html: string
  generated_at: string
}

export interface Overview {
  stats: {
    total_employees: number
    active_employees: number
    draft_banners: number
    signature_templates: number
    has_published_banner: boolean
  }
  current_banner: BannerWithHtml | null
  active_template: SignatureTemplate | null
}

export interface AuditLog {
  id: number
  user_id: number | null
  user_email: string | null
  action: string
  entity_type: string | null
  entity_id: string | null
  description: string | null
  created_at: string
}

export interface AppSettings {
  company_name: string
  company_website: string | null
  legal_disclaimer: string | null
  /** Whether the built-in company logo appears in email signatures. */
  show_logo_in_signature: boolean
  /** Outlook add-in: replace an employee's own Outlook default signature in new emails (default: keep it). */
  addin_replace_outlook_signature: boolean
  /** The built-in company logo (read-only). */
  company_logo_url: string
  /** Where Outlook and email recipients load images and the add-in from. */
  public_base_url: string
  updated_at: string
}

export interface OutlookStatus {
  addin: {
    last_seen_at: string
    last_source: 'auto' | 'button' | string
    last_status: 'inserted' | 'kept_outlook_default' | 'error' | string
    last_detail: string | null
    host: string | null
    /** Signed-in Outlook user's name (Office.js userProfile.displayName). */
    outlook_display_name: string | null
    outlook_email: string
    outlook_default_enabled: boolean | null
    last_inserted_at: string | null
  } | null
  classic_installed_at: string | null
  replace_outlook_signature: boolean
  /** Office add-ins cannot change Outlook's saved default signature - always false. */
  addin_can_set_default: boolean
}

export interface Branding {
  company_name: string
  company_logo_url: string
  /** Address used for images in emails (previews swap it for this app's own address). */
  public_base_url: string
}

export type AppSettingsInput = Omit<AppSettings, 'updated_at' | 'company_logo_url' | 'public_base_url'>

export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface MeResponse {
  user: User
  employee: Employee | null
}

export interface LoginResponse extends MeResponse {
  access_token: string
  token_type: string
  expires_at: string
}

export interface UploadResult {
  path: string
  url: string
}
