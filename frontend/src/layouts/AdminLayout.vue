<script setup lang="ts">
import { RouterLink, RouterView, useRoute } from 'vue-router'

const route = useRoute()

const menus = [
  { to: '/admin', label: '仪表盘', icon: '📊', exact: true },
  { to: '/admin/users', label: '用户管理', icon: '👥' },
  { to: '/admin/images', label: '图片管理', icon: '🖼' },
  { to: '/admin/announcements', label: '公告管理', icon: '📢' },
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
              class="flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm transition"
              :class="isActive(m.to, m.exact) ? 'bg-primary/15 border border-primary/20 text-primary-800 font-medium shadow-glass' : 'text-sub hover:bg-primary/5 border border-transparent'"
            >
              <span class="w-5 h-5 flex items-center justify-center text-xs shrink-0">{{ m.icon }}</span>
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
            class="shrink-0 px-4 py-1.5 rounded-full text-sm whitespace-nowrap transition"
            :class="isActive(m.to, m.exact) ? 'bg-primary/30 text-primary-800 border border-primary/30 font-medium' : 'bg-primary/5 text-primary-700 border border-primary/10 hover:bg-primary/15'"
          >
            {{ m.icon }} {{ m.label }}
          </RouterLink>
        </div>

        <RouterView />
      </div>
    </div>
  </div>
</template>