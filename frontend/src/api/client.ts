import axios, { AxiosError, type AxiosRequestConfig } from 'axios'
import type { ApiResponse } from '@/types'
import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  setTokens,
} from './token'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

// 请求拦截：注入 access token
api.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 登出/刷新重定向回调（由 auth store 注册，避免循环依赖）
let onUnauthorized: (() => void) | null = null
export function setUnauthorizedHandler(fn: (() => void) | null) {
  onUnauthorized = fn
}

// 正在刷新中的 Promise，避免并发多次刷新
let refreshing: Promise<string | null> | null = null

async function doRefresh(): Promise<string | null> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) return null
  try {
    const res = await axios.post(
      `${import.meta.env.VITE_API_BASE_URL || '/api/v1'}/auth/refresh`,
      { refresh_token: refreshToken },
    )
    const data = res.data as ApiResponse<{ access_token: string; refresh_token: string }>
    if (data.success && data.data) {
      setTokens(data.data.access_token, data.data.refresh_token)
      return data.data.access_token
    }
    return null
  } catch {
    return null
  }
}

// 响应拦截：统一解包 + 401 自动刷新重试一次
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as AxiosRequestConfig & { _retried?: boolean }
    const status = error.response?.status

    // 401 且未重试过且不是刷新请求本身
    if (status === 401 && !original._retried && original.url && !original.url.includes('/auth/refresh')) {
      original._retried = true
      refreshing = refreshing ?? doRefresh()
      const newToken = await refreshing
      refreshing = null
      if (newToken) {
        original.headers = original.headers ?? {}
        original.headers.Authorization = `Bearer ${newToken}`
        return api.request(original)
      }
      clearTokens()
      onUnauthorized?.()
    }
    return Promise.reject(error)
  },
)

// 统一 API 调用封装：自动解包 { success, data, error }
export async function request<T>(config: AxiosRequestConfig): Promise<T> {
  try {
    const res = await api.request<ApiResponse<T>>(config)
    const body = res.data
    if (!body.success) {
      throw new Error(body.error?.message ?? '请求失败')
    }
    return body.data as T
  } catch (e) {
    if (e instanceof AxiosError) {
      const detail = e.response?.data?.detail
      // 后端 HTTPException 返回 { detail: { code, message } }
      if (detail && typeof detail === 'object' && 'message' in detail) {
        throw new Error((detail as { message: string }).message)
      }
      if (typeof detail === 'string') {
        throw new Error(detail)
      }
      throw new Error(e.message || '网络请求失败')
    }
    throw e
  }
}

/**
 * 确保内存中有有效的 access token。
 * 页面刷新后 access token 丢失，此函数用 refresh token 静默换取新 token，
 * 避免首次请求因缺少凭证而产生 401 噪音。
 */
export async function ensureAccessToken(): Promise<string | null> {
  if (getAccessToken()) return getAccessToken()
  if (!getRefreshToken()) return null
  refreshing = refreshing ?? doRefresh()
  const token = await refreshing
  refreshing = null
  return token
}

export default api