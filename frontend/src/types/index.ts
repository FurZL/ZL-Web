export interface ApiResponse<T> {
  success: boolean
  data: T | null
  error: { code: string; message: string } | null
  request_id: string | null
}

export interface Page<T> {
  items: T[]
  pagination: { page: number; page_size: number; total: number }
}

export type Role =
  | 'guest'
  | 'member'
  | 'photographer'
  | 'moderator'
  | 'admin'
  | 'super_admin'

export interface User {
  id: string
  username: string
  displayName: string
  role: Role
  avatar: string
  bio: string
}

// 后端 /auth/me 返回的原始结构（snake_case）
export interface MeResponse {
  id: string
  username: string
  display_name: string
  email: string
  role: string
  status: string
  applied_role: string | null
  application_reason: string | null
  application_portfolio: string | null
  created_at: string
}

// 管理端用户（/admin/users 返回，snake_case）
export interface AdminUser {
  id: string
  username: string
  display_name: string
  email: string
  role: string
  status: string
  applied_role: string | null
  application_reason: string | null
  application_portfolio: string | null
  created_at: string
}

export interface GalleryImage {
  id: string
  url: string | null
  display_url: string | null
  thumb_url: string | null
  object_key: string | null
  original_name: string | null
  title: string
  description: string | null
  tags: string[]
  photographer: string
  moderation_status: string
  is_public: boolean
  width: number | null
  height: number | null
  uploaded_at: string | null
  processing_status: string | null
}

// 后端 /images/upload-intent 返回
export interface UploadIntent {
  storage_provider: string
  bucket: string
  object_key: string
  visibility: string
  upload_url: string
  expires_in: number
}

// 私有相册图片（/profile/me/images 返回）
export interface ProfileImage {
  id: string
  original_name: string | null
  description: string | null
  width: number | null
  height: number | null
  created_at: string | null
  processing_status: string | null
  thumb_url: string | null
}

export interface Announcement {
  id: string
  title: string
  summary: string
  date: string
  pinned: boolean
}

export interface CourseSlot {
  name: string
  location: string
  weekday: number // 0=周一 … 6=周日
  lessonStart: number
  lessonEnd: number
  weeks: number[]
  campus?: string
}

// ---------- 课表（真实 API 返回，snake_case） ----------
export interface ScheduleSlot {
  name: string
  location: string
  weekday: number // 0=周一 … 6=周日
  lesson_start: number
  lesson_end: number
  weeks: number[]
  campus: string | null
}

export interface ScheduleRecord {
  id: string
  original_name: string | null
  format: string | null
  slots: ScheduleSlot[]
  is_public: boolean
  created_at: string | null
  expires_at: string | null
  owner?: { id: string; username: string; display_name: string }
}

export interface ScheduleUploadIntent {
  storage_provider: string
  bucket: string
  object_key: string
  upload_url: string
  expires_in: number
}

export interface CompareFreeSlot {
  weekday: number
  lesson_start: number
  lesson_end: number
}

export interface CompareConflict {
  weekday: number
  a: ScheduleSlot
  b: ScheduleSlot
}

export interface ScheduleCompareResult {
  same_classroom: CompareConflict[]
  both_free: CompareFreeSlot[]
  overlaps: CompareConflict[]
}

// ---------- 站点配置 / 公告 ----------
export interface PublicConfig {
  site_name: string
  site_subtitle: string
  logo_url: string | null
  favicon_url: string | null
  icp_number: string | null
  police_number: string | null
}

export interface FooterLink {
  label: string
  href: string
}

export interface FooterConfig {
  links: FooterLink[]
  icp_number: string | null
  police_number: string | null
  copyright_owner: string
}

export interface LegalConfig {
  terms_url: string | null
  privacy_url: string | null
  copyright_notice: string | null
  contact_email: string | null
}

export interface ClubIntro {
  title: string
  content: string
}

export interface AnnouncementRecord {
  id: string
  title: string
  content: string
  status: string // draft / published / expired
  is_pinned: boolean
  published_at: string | null
  expires_at: string | null
  created_at: string | null
  updated_at: string | null
}

export interface SiteSettingRecord {
  key: string
  value: Record<string, unknown>
  category: string | null
  is_public: boolean
  updated_at: string | null
}