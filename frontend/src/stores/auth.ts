import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import type { Role, User } from '@/types'
import { members } from '@/api/mock'

export const useAuthStore = defineStore('auth', () => {
  // mock 登录态：null 表示未登录（演示登录流程，默认未登录）
  const user = ref<User | null>(null)
  const pendingApproval = ref(false)

  const role = computed<Role>(() => (user.value ? user.value.role : 'guest'))
  const isLoggedIn = computed(() => user.value !== null)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const isPhotographer = computed(() => user.value?.role === 'photographer' || user.value?.role === 'admin')

  function login(username: string) {
    const found = members.find((m) => m.username === username || m.displayName === username)
    user.value = found ?? {
      id: `u-${username}`,
      username,
      displayName: username,
      role: 'member',
      avatar: '',
      bio: '',
    }
  }

  function logout() {
    user.value = null
  }

  function submitRegistration() {
    pendingApproval.value = true
  }

  return {
    user,
    role,
    isLoggedIn,
    isAdmin,
    isPhotographer,
    pendingApproval,
    login,
    logout,
    submitRegistration,
  }
})