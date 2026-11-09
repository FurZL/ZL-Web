<script setup lang="ts">
import { RouterLink, RouterView, useRoute } from 'vue-router'

const route = useRoute()

const menus = [
  { to: '/admin', label: '仪表盘', icon: '📊', exact: true },
  { to: '/admin/users', label: '用户管理', icon: '👥' },
  { to: '/admin/images', label: '图片管理', icon: '🖼' },
  { to: '/admin/events', label: '活动管理', icon: '📅' },
  { to: '/admin/pages', label: '页面管理', icon: '📄' },
  { to: '/admin/settings', label: '网站设置', icon: '⚙' },
]

function isActive(to: string, exact: boolean | undefined) {
  if (exact) return route.path === to
  return route.path === to || route.path.startsWith(to + '/')
}
</script>

<template>
  <div class="max-w-6xl mx-auto px-4 py-8">
    <div class="flex gap-6">
      <!-- 侧边栏 -->
      <aside class="hidden md:block w-52 shrink-0">
        <div class="glass-card p-3 sticky top-20">
          <p class="px-3 py-2 text-xs font-semibold text-faint uppercase tracking-wide">管理后台</p>
          <nav class="space-y-1">
            <RouterLink
              v-for="m in menus"
              :key="m.to"
              :to="m.to"
              class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition"
              :class="isActive(m.to, m.exact) ? 'bg-primary text-white shadow-glow' : 'text-sub hover:bg-primary-50'"
            >
              <span>{{ m.icon }}</span>
              <span>{{ m.label }}</span>
            </RouterLink>
          </nav>
        </div>
      </aside>

      <!-- 内容区 -->
      <div class="flex-1 min-w-0">
        <!-- 移动端横滑菜单 -->
        <div class="md:hidden mb-4 overflow-x-auto flex gap-2 pb-1">
          <RouterLink
            v-for="m in menus"
            :key="m.to"
            :to="m.to"
            class="shrink-0 px-3 py-1.5 rounded-full text-sm whitespace-nowrap"
            :class="isActive(m.to, m.exact) ? 'bg-primary text-white' : 'bg-white/70 text-sub'"
          >
            {{ m.icon }} {{ m.label }}
          </RouterLink>
        </div>

        <RouterView />
      </div>
    </div>
  </div>
</template>