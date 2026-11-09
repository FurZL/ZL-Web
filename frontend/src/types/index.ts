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