import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import type { MeResponse, Role, User } from '@/types'
import { request, setUnauthorizedHandler } from '@/api/client'
import { clearTokens, getRefreshToken, setTokens } from '@/api/token'

interface LoginResult {
  access_token: string
  refresh_token: string
  user: { id: string; username: string; display_name: string; role: string }
}

function toUser(raw: MeResponse | LoginResult['user']): User {
  if ('display_name' in raw) {
    return {
      id: raw.id,
      username: raw.username,
      displayName: (raw as MeResponse).display_name ?? (raw as LoginResult['user']).display_name,
      role: (raw.role as Role) ?? 'member',
      avatar: (raw as MeResponse).avatar_url ?? '',
      bio: (raw as MeResponse).bio ?? '',
    }
  }
  return raw as unknown as User
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const loading = ref(false)

  const role = computed<Role>(() => (user.value ? user.value.role : 'guest'))
  const isLoggedIn = computed(() => user.value !== null)
  const isAdmin = computed(() => user.value?.role === 'admin' || user.value?.role === 'super_admin')
  const isPhotographer = computed(
    () => user.value?.role === 'photographer' || user.value?.role === 'admin' || user.value?.role === 'super_admin',
  )

  // 注册 401 处理器：令牌失效时登出
  setUnauthorizedHandler(() => {
    user.value = null
  })

  async function login(account: string, password: string) {
    loading.value = true
    try {
      const data = await request<LoginResult>({
        method: 'POST',
        url: '/auth/login',
        data: { account, password },
      })
      setTokens(data.access_token, data.refresh_token)
      user.value = toUser(data.user)
      return true
    } finally {
      loading.value = false
    }
  }

  async function fetchMe() {
    const data = await request<MeResponse>({ method: 'GET', url: '/auth/me' })
    user.value = toUser(data)
    return user.value
  }

  async function logout() {
    const refresh = getRefreshToken()
    if (refresh) {
      try {
        await request({ method: 'POST', url: '/auth/logout', data: { refresh_token: refresh } })
      } catch {
        // 忽略登出错误
      }
    }
    clearTokens()
    user.value = null
  }

  return {
    user,
    loading,
    role,
    isLoggedIn,
    isAdmin,
    isPhotographer,
    login,
    fetchMe,
    logout,
  }
})