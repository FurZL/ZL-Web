/** 图片管理 API */
import { request } from './client'
import type { AdminImageStats, GalleryImage } from '@/types'

export function adminGetImageStats() {
  return request<AdminImageStats>({ method: 'GET', url: '/admin/images/stats' })
}

export function adminListImages(params: {
  page?: number
  page_size?: number
  status?: string | null
  is_public?: boolean | null
}) {
  const query: Record<string, string> = {}
  if (params.page) query.page = String(params.page)
  if (params.page_size) query.page_size = String(params.page_size)
  if (params.status) query.status = params.status
  if (params.is_public !== null && params.is_public !== undefined) {
    query.is_public = String(params.is_public)
  }
  const qs = new URLSearchParams(query).toString()
  return request<{ items: GalleryImage[]; pagination: { page: number; page_size: number; total: number } }>({
    method: 'GET',
    url: `/admin/images/${qs ? '?' + qs : ''}`,
  })
}

export function adminSetImageModeration(imageId: string, moderationStatus: string) {
  return request<GalleryImage>({
    method: 'PATCH',
    url: `/admin/images/${imageId}/moderation`,
    data: { moderation_status: moderationStatus },
  })
}

export function adminSetImageVisibility(imageId: string, isPublic: boolean) {
  return request<GalleryImage>({
    method: 'PATCH',
    url: `/admin/images/${imageId}/visibility`,
    data: { is_public: isPublic },
  })
}

export function adminSetImageTags(imageId: string, tags: string[]) {
  return request<GalleryImage>({
    method: 'PUT',
    url: `/admin/images/${imageId}/tags`,
    data: { tags },
  })
}

export function adminDeleteImage(imageId: string) {
  return request<{ message: string }>({
    method: 'DELETE',
    url: `/admin/images/${imageId}`,
  })
}
