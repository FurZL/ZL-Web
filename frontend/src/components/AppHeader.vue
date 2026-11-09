<script setup lang="ts">
import { RouterLink } from 'vue-router'

const links = [
  { to: '/', label: '首页' },
  { to: '/gallery', label: '相册' },
  { to: '/schedule', label: '课表' },
  { to: '/events', label: '活动' },
  { to: '/about', label: '关于' },
]
</script>

<template>
  <header class="bg-white border-b border-neutral-200">
    <nav class="max-w-6xl mx-auto px-4 h-14 flex items-center gap-6">
      <RouterLink to="/" class="font-semibold text-primary">
        浙江理工福瑞圈
      </RouterLink>
      <RouterLink
        v-for="link in links"
        :key="link.to"
        :to="link.to"
        class="text-sm text-neutral-600 hover:text-primary"
      >
        {{ link.label }}
      </RouterLink>
      <span class="ml-auto text-sm text-neutral-400">Furry ZJUT</span>
    </nav>
  </header>
</template>