<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterView } from 'vue-router'
import AppFooter from '@/components/AppFooter.vue'
import AppHeader from '@/components/AppHeader.vue'
import AppDialog from '@/components/AppDialog.vue'
import { bootstrapAuth } from '@/api/bootstrap'

onMounted(() => {
  // 守卫也会调用它，这里只是保证正常首屏也有登录态
  void bootstrapAuth()
})
</script>

<template>
  <div class="min-h-screen flex flex-col bg-canvas text-ink">
    <AppHeader />
    <main class="flex-1">
      <RouterView />
    </main>
    <AppFooter />
    <AppDialog />
  </div>
</template>