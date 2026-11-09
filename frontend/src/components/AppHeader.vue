<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import UserAvatar from '@/components/UserAvatar.vue'

const auth = useAuthStore()
const menuOpen = ref(false)

const navLinks = [
  { to: '/', label: '首页' },
  { to: '/about', label: '社团介绍' },
  { to: '/gallery', label: '图片展示' },
  ...(auth.isLoggedIn ? [{ to: '/schedule', label: '课表工具' }] : []),
]

function toggleMenu() {
  menuOpen.value = !menuOpen.value
}
</script>

<template>
  <header class="topbar">
    <nav class="max-w-6xl mx-auto px-4 h-16 flex items-center gap-6">
      <RouterLink to="/" class="flex items-center gap-2 shrink-0">
        <span class="w-9 h-8 rounded-xl bg-hero-gradient flex items-center justify-center text-white font-bold shadow-soft tracking-tight text-[10px]">
          FUR
        </span>
        <span class="hidden lg:inline font-semibold text-ink tracking-wide">浙江理工福瑞圈</span>
      </RouterLink>

      <div class="flex items-center gap-1 overflow-x-auto no-scrollbar">
        <RouterLink
          v-for="link in navLinks"
          :key="link.to"
          :to="link.to"
          class="shrink-0 px-3 py-2 text-sm rounded-lg text-sub hover:text-primary-700 hover:bg-primary-50 transition"
          active-class="text-primary-700 bg-primary-50 font-medium"
        >
          {{ link.label }}
        </RouterLink>
      </div>

      <div class="ml-auto flex items-center gap-3">
        <!-- 未登录 -->
        <template v-if="!auth.isLoggedIn">
          <RouterLink to="/login" class="text-sm text-sub hover:text-primary-700 px-3 py-2">登录</RouterLink>
          <RouterLink to="/register" class="btn-primary !px-5 !py-2">注册</RouterLink>
        </template>

        <!-- 已登录 -->
        <template v-else>
          <RouterLink
            v-if="auth.isPhotographer"
            to="/gallery?upload=1"
            class="hidden sm:inline-flex items-center gap-1.5 text-sm text-primary-700 bg-primary-50 hover:bg-primary-100 rounded-full px-4 py-2 transition"
          >
            上传图片
          </RouterLink>

          <div class="relative">
            <button class="flex items-center gap-2" @click="toggleMenu">
              <UserAvatar :name="auth.user!.displayName" :size="36" />
              <span class="hidden sm:block text-sm text-ink">{{ auth.user!.displayName }}</span>
              <span class="text-faint text-xs">▼</span>
            </button>

            <transition name="menu">
              <div
                v-if="menuOpen"
                class="absolute right-0 mt-2 w-44 glass-card p-1.5 z-50"
                @click="menuOpen = false"
              >
                <RouterLink to="/profile" class="block px-3 py-2 text-sm rounded-lg hover:bg-primary-50 text-ink">
                  个人空间
                </RouterLink>
                <RouterLink
                  v-if="auth.isLoggedIn"
                  to="/schedule"
                  class="block px-3 py-2 text-sm rounded-lg hover:bg-primary-50 text-ink"
                >
                  课表工具
                </RouterLink>
                <RouterLink
                  v-if="auth.isAdmin"
                  to="/admin"
                  class="block px-3 py-2 text-sm rounded-lg hover:bg-primary-50 text-ink"
                >
                  管理后台
                </RouterLink>
                <button
                  class="w-full text-left px-3 py-2 text-sm rounded-lg hover:bg-primary-50 text-sub"
                  @click="auth.logout()"
                >
                  退出
                </button>
              </div>
            </transition>
          </div>
        </template>
      </div>
    </nav>
  </header>
</template>

<style scoped>
.menu-enter-active,
.menu-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.menu-enter-from,
.menu-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
.no-scrollbar::-webkit-scrollbar {
  display: none;
}
.no-scrollbar {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
</style>