<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterView } from 'vue-router'
import AppFooter from '@/components/AppFooter.vue'
import AppHeader from '@/components/AppHeader.vue'
import { useAuthStore } from '@/stores/auth'
import { getRefreshToken } from '@/api/token'
import { ensureAccessToken } from '@/api/client'

const auth = useAuthStore()

onMounted(async () => {
  // 页面刷新后：若有 refresh token，先静默换取 access token 再请求，
  // 避免首次 fetchMe 因缺少凭证产生 401 噪音。
  if (getRefreshToken()) {
    try {
      await ensureAccessToken()
      await auth.fetchMe()
    } catch {
      // 刷新失败则保持未登录
    }
  }
})
</script>

<template>
  <div class="min-h-screen flex flex-col bg-canvas text-ink">
    <AppHeader />
    <main class="flex-1">
      <RouterView />
    </main>
    <AppFooter />
  </div>
</template>