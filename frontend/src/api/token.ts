/** token 内存管理：access_token 仅存内存，refresh_token 持久化到 sessionStorage。 */

const REFRESH_KEY = 'refresh_token'

let accessToken: string | null = null
let refreshToken: string | null = sessionStorage.getItem(REFRESH_KEY)

export function getAccessToken(): string | null {
  return accessToken
}

export function setTokens(access: string, refresh: string) {
  accessToken = access
  refreshToken = refresh
  sessionStorage.setItem(REFRESH_KEY, refresh)
}

export function getRefreshToken(): string | null {
  return refreshToken
}

export function clearTokens() {
  accessToken = null
  refreshToken = null
  sessionStorage.removeItem(REFRESH_KEY)
}