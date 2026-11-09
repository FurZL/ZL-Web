<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import UserAvatar from '@/components/UserAvatar.vue'

const auth = useAuthStore()
const menuOpen = ref(false)

const navLinks = computed(() => [
  { to: '/', label: '首页' },
  { to: '/about', label: '社团介绍' },
  { to: '/gallery', label: '图片展示' },
  { to: '/events', label: '活动' },
  ...(auth.isLoggedIn ? [{ to: '/schedule', label: '课表' }] : []),
])

function toggleMenu() {
  menuOpen.value = !menuOpen.value
  if (menuOpen.value) {
    nextTick(updateMenuPos)
    setTimeout(() => document.addEventListener('click', onClickOutside), 0)
  } else {
    document.removeEventListener('click', onClickOutside)
  }
}

function closeMenu() {
  menuOpen.value = false
  document.removeEventListener('click', onClickOutside)
}

function onClickOutside(e: MouseEvent) {
  if (triggerRef.value && !triggerRef.value.contains(e.target as Node)) {
    closeMenu()
  }
}

const triggerRef = ref<HTMLElement | null>(null)
const headerRef = ref<HTMLElement | null>(null)
const menuStyle = ref<Record<string, string>>({})

function updateMenuPos() {
  const btn = triggerRef.value
  const header = headerRef.value
  if (!btn) return
  const btnRect = btn.getBoundingClientRect()
  const headerBottom = header ? header.getBoundingClientRect().bottom : btnRect.bottom
  menuStyle.value = {
    position: 'fixed',
    top: `${headerBottom}px`,
    right: `${window.innerWidth - btnRect.right - 12}px`,
    zIndex: '200',
    background: 'rgba(255, 255, 255, 0.7)',
    backdropFilter: 'blur(24px)',
    WebkitBackdropFilter: 'blur(24px)',
  }
}

function onScrollOrResize() {
  if (menuOpen.value) updateMenuPos()
}

onMounted(() => {
  window.addEventListener('scroll', onScrollOrResize, true)
  window.addEventListener('resize', onScrollOrResize)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', onClickOutside)
  window.removeEventListener('scroll', onScrollOrResize, true)
  window.removeEventListener('resize', onScrollOrResize)
})
</script>

<template>
  <header ref="headerRef" class="topbar">
    <nav class="max-w-6xl mx-auto px-4 h-16 flex items-center gap-6">
      <RouterLink to="/" class="flex items-center gap-2 shrink-0">
        <span class="w-9 h-8 rounded-xl bg-hero-gradient flex items-center justify-center text-white font-bold shadow-soft tracking-tight text-[10px]">
          FUR
        </span>
        <span class="hidden lg:inline font-semibold text-ink tracking-wide">浙江理工福瑞圈</span>
      </RouterLink>

      <div class="flex items-center gap-2 overflow-x-auto no-scrollbar">
        <RouterLink
          v-for="link in navLinks"
          :key="link.to"
          :to="link.to"
          class="shrink-0 px-3 py-1.5 text-[13px] rounded-lg text-primary-700 bg-primary/5 border border-primary/10 hover:bg-primary/15 transition"
          active-class="bg-primary/40 border-primary/40 text-primary-900 font-medium"
        >
          {{ link.label }}
        </RouterLink>
      </div>

      <div class="ml-auto flex items-center gap-3.5">
        <template v-if="!auth.isLoggedIn">
          <RouterLink to="/login" class="text-[13px] font-medium text-primary-700 bg-primary/5 border border-primary/10 hover:bg-primary/15 rounded-lg px-3 py-1.5 transition">
            登录
          </RouterLink>
          <RouterLink to="/register" class="text-[13px] font-medium text-primary-700 bg-primary/15 border border-primary/20 hover:bg-primary/25 rounded-lg px-3.5 py-1.5 shadow-glass transition">
            注册
          </RouterLink>
        </template>

        <template v-else>
          <button ref="triggerRef" class="flex items-center gap-2" @click.stop="toggleMenu">
            <UserAvatar :name="auth.user!.displayName" :size="36" />
            <span class="hidden sm:block text-sm text-ink">{{ auth.user!.displayName }}</span>
            <!-- CSS 三角形箭头 -->
            <span
              class="inline-block border-solid transition-transform duration-200"
              :class="menuOpen ? 'rotate-180' : ''"
              style="width:0;height:0;border-left:4px solid transparent;border-right:4px solid transparent;border-top:5px solid currentColor;"
            ></span>
          </button>
        </template>
      </div>
    </nav>
  </header>

  <!-- 菜单传送到 body 层，脱离 topbar 的 backdrop-blur 层叠上下文 -->
  <Teleport to="body">
    <transition name="menu">
      <div
        v-if="menuOpen"
        class="w-44 rounded-xl2 border border-white/60 shadow-glass p-1.5"
        :style="menuStyle"
        @click="closeMenu"
      >
        <RouterLink to="/profile" class="block px-3 py-2 text-sm rounded-xl2 hover:bg-primary-50 text-ink">
          个人空间
        </RouterLink>
        <RouterLink to="/schedule" class="block px-3 py-2 text-sm rounded-xl2 hover:bg-primary-50 text-ink">
          课表
        </RouterLink>
        <RouterLink v-if="auth.isAdmin" to="/admin" class="block px-3 py-2 text-sm rounded-xl2 hover:bg-primary-50 text-ink">
          管理后台
        </RouterLink>
        <button class="w-full text-left px-3 py-2 text-sm rounded-xl2 hover:bg-primary-50 text-sub" @click="auth.logout()">
          退出
        </button>
      </div>
    </transition>
  </Teleport>
</template>

<style scoped>
.menu-enter-active,
.menu-leave-active {
  transition: opacity 0.15s ease;
}
.menu-enter-from,
.menu-leave-to {
  opacity: 0;
}
.no-scrollbar::-webkit-scrollbar {
  display: none;
}
.no-scrollbar {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
</style>
