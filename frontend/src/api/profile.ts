/** 个人主页客制化 API：公开读取 + 本人草稿/发布/主题 */
import { request } from './client'
import type {
  ProfileBlock,
  ProfileLayoutResponse,
  ProfileMediaOption,
  ProfilePageResponse,
  ProfileTheme,
} from '@/types'

// ---------- 公开 ----------

/** 读取某用户已发布的主页；未发布或已隐藏时后端返回 404 PROFILE_PAGE_NOT_FOUND */
export function getProfilePage(username: string): Promise<ProfilePageResponse> {
  return request<ProfilePageResponse>({
    method: 'GET',
    url: `/profile/${encodeURIComponent(username)}/page`,
  })
}

// ---------- 本人 ----------

export function getMyLayout(): Promise<ProfileLayoutResponse> {
  return request<ProfileLayoutResponse>({ method: 'GET', url: '/profile/me/layout' })
}

/** 整体替换草稿；保存不影响公开页，直到调用 publishMyLayout */
export function saveMyLayout(payload: {
  blocks: ProfileBlock[]
  is_public?: boolean
}): Promise<ProfileLayoutResponse> {
  return request<ProfileLayoutResponse>({
    method: 'PUT',
    url: '/profile/me/layout',
    data: payload,
  })
}

export function publishMyLayout(): Promise<{ published_at: string | null }> {
  return request<{ published_at: string | null }>({
    method: 'POST',
    url: '/profile/me/layout/publish',
  })
}

export function discardMyDraft(): Promise<ProfileLayoutResponse> {
  return request<ProfileLayoutResponse>({ method: 'POST', url: '/profile/me/layout/discard' })
}

export function saveMyTheme(theme: ProfileTheme): Promise<{ theme: ProfileTheme }> {
  return request<{ theme: ProfileTheme }>({
    method: 'PUT',
    url: '/profile/me/theme',
    data: theme,
  })
}

/** 可引用为模块素材的私有图片清单 */
export function getMyMedia(): Promise<{ items: ProfileMediaOption[] }> {
  return request<{ items: ProfileMediaOption[] }>({ method: 'GET', url: '/profile/me/media' })
}

/**
 * 标记某张私有图是否允许出现在公开主页。
 * is_displayable 默认 false：没有这一步，photo_wall 在公开页永远是空的。
 */
export function setProfileImageDisplayable(
  id: string,
  is_displayable: boolean,
): Promise<{ id: string; is_displayable: boolean }> {
  return request<{ id: string; is_displayable: boolean }>({
    method: 'PATCH',
    url: `/profile/me/images/${id}`,
    data: { is_displayable },
  })
}
