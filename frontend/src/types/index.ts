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

export type Role = 'guest' | 'member' | 'photographer' | 'admin'

export interface User {
  id: string
  username: string
  displayName: string
  role: Role
  avatar: string
  bio: string
}

export interface GalleryImage {
  id: string
  url: string
  title: string
  tags: string[]
  photographer: string
  width: number
  height: number
  uploadedAt: string
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