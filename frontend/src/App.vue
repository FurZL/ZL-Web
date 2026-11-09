<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterView } from 'vue-router'
import AppFooter from '@/components/AppFooter.vue'
import AppHeader from '@/components/AppHeader.vue'
import { useAuthStore } from '@/stores/auth'
import { getRefreshToken } from '@/api/token'

const auth = useAuthStore()

onMounted(async () => {
  // 页面刷新后：若有 refresh token，尝试恢复登录态
  if (getRefreshToken()) {
    try {
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