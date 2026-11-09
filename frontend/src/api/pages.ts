/** 动态页面 API：公开读取 + 管理 CRUD + 版本回滚 */
import { request } from './client'
import type { PageRecord, PageVersion } from '@/types'

// ---------- 公开 ----------

export function getPublishedPage(slug: string) {
  return request<PageRecord>({ method: 'GET', url: `/pages/${encodeURIComponent(slug)}` })
}

// ---------- 管理端 ----------

export function adminListPages() {
  return request<{ items: PageRecord[] }>({ method: 'GET', url: '/pages/admin/list' })
}

export function adminCreatePage(data: {
  slug: string
  title: string
  description?: string | null
  page_schema: Record<string, unknown>
  starts_at?: string | null
  ends_at?: string | null
  seo_title?: string | null
  seo_description?: string | null
}) {
  return request<PageRecord>({ method: 'POST', url: '/pages/admin', data })
}

export function adminGetPage(pageId: string) {
  return request<PageRecord>({ method: 'GET', url: `/pages/admin/${pageId}` })
}

export function adminUpdatePage(
  pageId: string,
  data: {
    title?: string
    description?: string | null
    page_schema?: Record<string, unknown>
    starts_at?: string | null
    ends_at?: string | null
    seo_title?: string | null
    seo_description?: string | null
    change_summary?: string | null
  },
) {
  return request<PageRecord>({ method: 'PUT', url: `/pages/admin/${pageId}`, data })
}

export function adminPublishPage(pageId: string) {
  return request<PageRecord>({ method: 'POST', url: `/pages/admin/${pageId}/publish` })
}

export function adminUnpublishPage(pageId: string) {
  return request<PageRecord>({ method: 'POST', url: `/pages/admin/${pageId}/unpublish` })
}

export function adminDeletePage(pageId: string) {
  return request<{ message: string }>({ method: 'DELETE', url: `/pages/admin/${pageId}` })
}

export function adminListVersions(pageId: string) {
  return request<{ items: PageVersion[] }>({
    method: 'GET',
    url: `/pages/admin/${pageId}/versions`,
  })
}

export function adminRollbackPage(pageId: string, versionId: string) {
  return request<PageRecord>({
    method: 'POST',
    url: `/pages/admin/${pageId}/rollback/${versionId}`,
  })
}
