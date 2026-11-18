/**
 * token 内存管理：
 * - access_token 仅存内存。
 * - refresh_token 由后端写入 HttpOnly Cookie，跨标签页共享，前端不读取也不存储。
 */

let accessToken: string | null = null
const SESSION_MARKER_KEY = 'auth_session'

export function getAccessToken(): string | null {
  return accessToken
}

export function hasSessionMarker(): boolean {
  return localStorage.getItem(SESSION_MARKER_KEY) === '1'
}

export function setAccessToken(access: string) {
  accessToken = access
  localStorage.setItem(SESSION_MARKER_KEY, '1')
}

export function clearTokens() {
  accessToken = null
  localStorage.removeItem(SESSION_MARKER_KEY)
}
