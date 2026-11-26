<script setup lang="ts">
import { RouterLink, RouterView, useRoute } from 'vue-router'

const route = useRoute()

const menus = [
  { to: '/admin', label: '仪表盘', icon: '📊', exact: true },
  { to: '/admin/users', label: '用户管理', icon: '👥' },
  { to: '/admin/images', label: '图片管理', icon: '🖼' },
  { to: '/admin/schedule', label: '课表运营', icon: '📅' },
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
        <!-- 移动端菜单在空间不足时均分为两行。 -->
        <nav aria-label="管理后台导航" class="admin-mobile-nav md:hidden mb-5">
          <RouterLink
            v-for="m in menus"
            :key="m.to"
            :to="m.to"
            class="admin-mobile-nav__item transition"
            :class="isActive(m.to, m.exact) ? 'bg-primary/30 text-primary-800 border border-primary/30 font-medium' : 'bg-primary/5 text-primary-700 border border-primary/10 hover:bg-primary/15'"
            :aria-current="isActive(m.to, m.exact) ? 'page' : undefined"
          >
            {{ m.label }}
          </RouterLink>
        </nav>

        <RouterView />
      </div>
    </div>
  </div>
</template>

<style scoped>
.admin-mobile-nav {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 6px;
}

.admin-mobile-nav__item {
  display: flex;
  min-width: 0;
  min-height: 40px;
  align-items: center;
  justify-content: center;
  padding: 4px 2px;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.25;
  text-align: center;
  white-space: nowrap;
}

@media (min-width: 640px) {
  .admin-mobile-nav {
    grid-template-columns: repeat(8, minmax(0, 1fr));
    gap: 4px;
  }
}

@media (min-width: 768px) {
  .admin-mobile-nav {
    display: none;
  }
}

@media (max-width: 340px) {
  .admin-mobile-nav__item {
    font-size: 13px;
  }
}
</style>
