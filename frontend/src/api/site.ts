/** 站点配置 / 公告 API */
import { request } from './client'
import type {
  AnnouncementRecord,
  ClubIntro,
  FooterConfig,
  LegalConfig,
  PublicConfig,
  SiteSettingRecord,
} from '@/types'

// ---------- 公开端点 ----------

export function getPublicConfig() {
  return request<PublicConfig>({ method: 'GET', url: '/site/public-config' })
}

export function getFooter() {
  return request<FooterConfig>({ method: 'GET', url: '/site/footer' })
}

export function getLegal() {
  return request<LegalConfig>({ method: 'GET', url: '/site/legal' })
}

export function getClubIntro() {
  return request<ClubIntro>({ method: 'GET', url: '/club/intro' })
}

export function getPublishedAnnouncements() {
  return request<{ items: AnnouncementRecord[] }>({
    method: 'GET',
    url: '/announcements/published',
  })
}

// ---------- 管理端点 ----------

export function getAllAnnouncements() {
  return request<{ items: AnnouncementRecord[] }>({
    method: 'GET',
    url: '/announcements/admin',
  })
}

export function createAnnouncement(data: {
  title: string
  content: string
  is_pinned?: boolean
  publish_now?: boolean
  expires_at?: string | null
}) {
  return request<AnnouncementRecord>({
    method: 'POST',
    url: '/announcements/admin',
    data,
  })
}

export function updateAnnouncement(
  id: string,
  data: {
    title?: string
    content?: string
    is_pinned?: boolean
    publish_now?: boolean
    expires_at?: string | null
  },
) {
  return request<AnnouncementRecord>({
    method: 'PATCH',
    url: `/announcements/admin/${id}`,
    data,
  })
}

export function deleteAnnouncement(id: string) {
  return request<{ message: string }>({
    method: 'DELETE',
    url: `/announcements/admin/${id}`,
  })
}

export function getAdminSettings() {
  return request<{ items: SiteSettingRecord[] }>({
    method: 'GET',
    url: '/admin/settings/',
  })
}

export function upsertSetting(data: {
  key: string
  value: Record<string, unknown>
  category?: string | null
  is_public?: boolean
}) {
  return request<SiteSettingRecord>({
    method: 'PUT',
    url: '/admin/settings/',
    data,
  })
}

export function updateClubIntro(data: ClubIntro) {
  return request<SiteSettingRecord>({
    method: 'PUT',
    url: '/club/intro',
    data,
  })
}
