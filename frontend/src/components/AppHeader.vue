<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useSiteConfig } from '@/composables/useSiteConfig'
import UserAvatar from '@/components/UserAvatar.vue'

const auth = useAuthStore()
const route = useRoute()
const { siteName, siteSubtitle, registrationConfig } = useSiteConfig()

const accountOpen = ref(false)
const mobileOpen = ref(false)
const triggerRef = ref<HTMLElement | null>(null)
const headerRef = ref<HTMLElement | null>(null)
const mobileCloseRef = ref<HTMLElement | null>(null)
const accountMenuStyle = ref<Record<string, string>>({})
let previousBodyOverflow = ''

const navLinks = computed(() => [
  { to: '/', label: '首页' },
  { to: '/about', label: '社团介绍' },
  { to: '/gallery', label: '图片展示' },
  { to: '/events', label: '活动' },
  ...(auth.isLoggedIn ? [{ to: '/schedule', label: '课表' }] : []),
])

const mobileAccountLinks = computed(() => {
  if (!auth.isLoggedIn) return []
  return [
    { to: '/profile', label: '个人空间' },
    ...(auth.isAdmin ? [{ to: '/admin', label: '管理后台' }] : []),
  ]
})

function toggleAccount() {
  accountOpen.value = !accountOpen.value
  if (accountOpen.value) {
    nextTick(updateAccountMenuPos)
    setTimeout(() => document.addEventListener('click', onAccountClickOutside), 0)
  } else {
    document.removeEventListener('click', onAccountClickOutside)
  }
}

function closeAccount() {
  accountOpen.value = false
  document.removeEventListener('click', onAccountClickOutside)
}

function onAccountClickOutside(event: MouseEvent) {
  if (triggerRef.value && !triggerRef.value.contains(event.target as Node)) {
    closeAccount()
  }
}

function updateAccountMenuPos() {
  const button = triggerRef.value
  if (!button) return
  const buttonRect = button.getBoundingClientRect()
  const headerBottom = headerRef.value?.getBoundingClientRect().bottom ?? buttonRect.bottom
  accountMenuStyle.value = {
    position: 'fixed',
    top: `${headerBottom}px`,
    right: `${window.innerWidth - buttonRect.right - 12}px`,
    zIndex: '210',
  }
}

function openMobileMenu() {
  closeAccount()
  mobileOpen.value = true
}

function closeMobileMenu() {
  mobileOpen.value = false
}

function onKeydown(event: KeyboardEvent) {
  if (event.key !== 'Escape') return
  if (mobileOpen.value) closeMobileMenu()
  if (accountOpen.value) closeAccount()
}

function onScrollOrResize() {
  if (accountOpen.value) updateAccountMenuPos()
  if (window.innerWidth >= 1024 && mobileOpen.value) closeMobileMenu()
}

function logoutAndRedirect() {
  void auth.logout().finally(() => {
    window.location.href = '/'
  })
}

watch(mobileOpen, async (open) => {
  if (open) {
    previousBodyOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    await nextTick()
    mobileCloseRef.value?.focus()
  } else {
    document.body.style.overflow = previousBodyOverflow
  }
})

watch(
  () => route.fullPath,
  () => {
    closeMobileMenu()
    closeAccount()
  },
)

onMounted(() => {
  document.addEventListener('keydown', onKeydown)
  window.addEventListener('scroll', onScrollOrResize, true)
  window.addEventListener('resize', onScrollOrResize)
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKeydown)
  document.removeEventListener('click', onAccountClickOutside)
  window.removeEventListener('scroll', onScrollOrResize, true)
  window.removeEventListener('resize', onScrollOrResize)
  document.body.style.overflow = previousBodyOverflow
})
</script>

<template>
  <header ref="headerRef" class="topbar">
    <nav class="max-w-6xl mx-auto px-4 h-16 flex items-center gap-3 sm:gap-6" aria-label="站点导航">
      <RouterLink to="/" class="flex items-center gap-2 shrink-0" @click="closeMobileMenu">
        <img
          src="/logo-m-96.png"
          :alt="siteName"
          width="36"
          height="36"
          class="w-9 h-9 rounded-xl object-contain bg-white/80 border border-white/60 shadow-soft"
        />
        <span class="hidden sm:inline font-semibold text-ink tracking-wide">{{ siteName }}</span>
      </RouterLink>

      <div class="hidden lg:flex items-center gap-2">
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

      <div class="ml-auto flex items-center gap-2">
        <div class="hidden lg:flex items-center gap-3.5">
          <template v-if="!auth.isLoggedIn">
            <RouterLink
              to="/login"
              class="text-[13px] font-medium text-primary-700 bg-primary/5 border border-primary/10 hover:bg-primary/15 rounded-lg px-3 py-1.5 transition"
            >
              登录
            </RouterLink>
            <RouterLink
              v-if="registrationConfig.registration_enabled"
              to="/register"
              class="text-[13px] font-medium text-primary-700 bg-primary/15 border border-primary/20 hover:bg-primary/25 rounded-lg px-3.5 py-1.5 shadow-glass transition"
            >
              注册
            </RouterLink>
          </template>

          <button
            v-else
            ref="triggerRef"
            class="flex items-center gap-2"
            :aria-expanded="accountOpen"
            aria-haspopup="menu"
            aria-label="打开账号菜单"
            @click.stop="toggleAccount"
          >
            <UserAvatar :name="auth.user!.displayName" :size="36" :src="auth.user!.avatar || null" />
            <span class="hidden sm:block text-sm text-ink">{{ auth.user!.displayName }}</span>
            <span
              class="inline-block border-solid transition-transform duration-200"
              :class="accountOpen ? 'rotate-180' : ''"
              style="width:0;height:0;border-left:4px solid transparent;border-right:4px solid transparent;border-top:5px solid currentColor;"
            ></span>
          </button>
        </div>

        <button
          type="button"
          class="lg:hidden inline-flex h-10 w-10 items-center justify-center rounded-xl border border-primary/15 bg-white/65 text-primary-700 transition hover:bg-primary-50 active:scale-95"
          :aria-expanded="mobileOpen"
          aria-controls="mobile-navigation"
          aria-label="打开导航菜单"
          @click="openMobileMenu"
        >
          <span class="flex w-5 flex-col gap-[5px]" aria-hidden="true">
            <span class="h-0.5 w-full rounded-full bg-current"></span>
            <span class="h-0.5 w-full rounded-full bg-current"></span>
            <span class="h-0.5 w-full rounded-full bg-current"></span>
          </span>
        </button>
      </div>
    </nav>
  </header>

  <!-- 桌面端账号菜单 -->
  <Teleport to="body">
    <transition name="menu">
      <div
        v-if="accountOpen"
        class="w-44 rounded-xl2 border border-white/60 shadow-glass p-1.5"
        :style="{ ...accountMenuStyle, background: 'rgba(255, 255, 255, 0.78)', backdropFilter: 'blur(24px)', WebkitBackdropFilter: 'blur(24px)' }"
        role="menu"
        @click="closeAccount"
      >
        <RouterLink to="/profile" class="block px-3 py-2 text-sm rounded-xl2 hover:bg-primary-50 text-ink" role="menuitem">
          个人空间
        </RouterLink>
        <RouterLink to="/schedule" class="block px-3 py-2 text-sm rounded-xl2 hover:bg-primary-50 text-ink" role="menuitem">
          课表
        </RouterLink>
        <RouterLink v-if="auth.isAdmin" to="/admin" class="block px-3 py-2 text-sm rounded-xl2 hover:bg-primary-50 text-ink" role="menuitem">
          管理后台
        </RouterLink>
        <button
          class="w-full text-left px-3 py-2 text-sm rounded-xl2 hover:bg-primary-50 text-sub"
          role="menuitem"
          @click="logoutAndRedirect"
        >
          退出
        </button>
      </div>
    </transition>
  </Teleport>

  <!-- 移动端 / 窄屏抽屉导航 -->
  <Teleport to="body">
    <transition name="drawer">
      <div v-if="mobileOpen" class="fixed inset-0 z-[250] lg:hidden">
        <div class="absolute inset-0 bg-ink/35 backdrop-blur-[2px]" @click="closeMobileMenu"></div>
        <aside
          id="mobile-navigation"
          class="drawer-panel absolute inset-y-0 right-0 flex w-[min(88vw,21rem)] flex-col border-l border-white/70"
          role="dialog"
          aria-modal="true"
          aria-label="移动导航菜单"
        >
          <div class="flex items-center justify-between border-b border-ink/10 px-5 py-4">
            <RouterLink to="/" class="flex min-w-0 items-center gap-2.5" @click="closeMobileMenu">
              <img
                src="/logo-m-96.png"
                :alt="siteName"
                width="36"
                height="36"
                class="h-9 w-9 shrink-0 rounded-xl object-contain bg-white/80 border border-white/60 shadow-soft"
              />
              <span class="truncate font-semibold text-ink">{{ siteName }}</span>
            </RouterLink>
            <button
              ref="mobileCloseRef"
              type="button"
              class="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-xl leading-none text-sub transition hover:bg-ink/5 hover:text-ink"
              aria-label="关闭导航菜单"
              @click="closeMobileMenu"
            >
              ×
            </button>
          </div>

          <div class="min-h-0 flex-1 overflow-y-auto px-5 py-5">
            <div v-if="auth.isLoggedIn" class="rounded-2xl border border-primary-100/80 bg-primary-50/70 p-4">
              <div class="flex items-center gap-3">
                <UserAvatar :name="auth.user!.displayName" :size="44" :src="auth.user!.avatar || null" />
                <div class="min-w-0">
                  <p class="truncate font-medium text-ink">{{ auth.user!.displayName }}</p>
                  <p class="truncate text-xs text-sub">@{{ auth.user!.username }}</p>
                </div>
              </div>
            </div>
            <div v-else class="rounded-2xl border border-primary-100/80 bg-primary-50/60 p-4">
              <p class="font-medium text-ink">欢迎来到{{ siteName }}</p>
              <p class="mt-1 text-xs leading-5 text-sub">{{ siteSubtitle }}</p>
            </div>

            <nav class="mt-5 space-y-1" aria-label="主导航">
              <RouterLink
                v-for="link in navLinks"
                :key="link.to"
                :to="link.to"
                class="flex items-center rounded-xl px-4 py-3 text-sm font-medium text-ink transition hover:bg-primary-50"
                active-class="!bg-primary/10 !text-primary-800"
                @click="closeMobileMenu"
              >
                {{ link.label }}
              </RouterLink>

              <div v-if="mobileAccountLinks.length" class="my-2 border-t border-ink/10"></div>
              <RouterLink
                v-for="link in mobileAccountLinks"
                :key="link.to"
                :to="link.to"
                class="flex items-center rounded-xl px-4 py-3 text-sm font-medium text-ink transition hover:bg-primary-50"
                active-class="!bg-primary/10 !text-primary-800"
                @click="closeMobileMenu"
              >
                {{ link.label }}
              </RouterLink>
            </nav>

            <div v-if="!auth.isLoggedIn" class="mt-6 grid gap-2.5">
              <RouterLink to="/login" class="btn-primary w-full" @click="closeMobileMenu">
                登录
              </RouterLink>
              <RouterLink
                v-if="registrationConfig.registration_enabled"
                to="/register"
                class="btn-ghost w-full"
                @click="closeMobileMenu"
              >
                注册
              </RouterLink>
            </div>

            <button
              v-else
              type="button"
              class="mt-6 w-full rounded-xl border border-ink/10 px-4 py-3 text-left text-sm text-sub transition hover:border-blush/40 hover:bg-blush/5 hover:text-blush"
              @click="logoutAndRedirect"
            >
              退出登录
            </button>
          </div>

          <div class="border-t border-ink/10 px-5 py-4 text-xs text-faint">
            {{ siteName }} · 温暖、可爱、有社群感
          </div>
        </aside>
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

.drawer-panel {
  background: rgba(251, 251, 255, 0.96);
  backdrop-filter: blur(28px);
  -webkit-backdrop-filter: blur(28px);
  box-shadow: -18px 0 48px rgba(31, 27, 51, 0.16);
}

.drawer-enter-active,
.drawer-leave-active {
  transition: opacity 0.24s ease;
}
.drawer-enter-active .drawer-panel,
.drawer-leave-active .drawer-panel {
  transition: transform 0.28s cubic-bezier(0.22, 1, 0.36, 1);
}
.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
}
.drawer-enter-from .drawer-panel,
.drawer-leave-to .drawer-panel {
  transform: translateX(100%);
}

@media (prefers-reduced-motion: reduce) {
  .drawer-enter-active,
  .drawer-leave-active,
  .drawer-enter-active .drawer-panel,
  .drawer-leave-active .drawer-panel {
    transition: none;
  }
}
</style>
