<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useSiteConfig } from '@/composables/useSiteConfig'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const { siteName } = useSiteConfig()

const account = ref('')
const password = ref('')
const error = ref('')
const submitting = ref(false)

async function submit() {
  if (!account.value || !password.value) {
    error.value = '请输入账号和密码'
    return
  }
  error.value = ''
  submitting.value = true
  try {
    await auth.login(account.value, password.value)
    const redirect = (route.query.redirect as string) || '/'
    router.push(redirect)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '登录失败，请重试'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="max-w-md mx-auto px-4 py-16">
    <div class="glass-card p-8">
      <div class="text-center">
        <img
          src="/logo-m.png"
          :alt="siteName"
          width="72"
          height="72"
          class="w-[72px] h-[72px] rounded-2xl object-contain bg-white/80 border border-white/60 shadow-soft mx-auto"
        />
        <h1 class="mt-4 text-2xl font-bold text-ink">欢迎回来</h1>
        <p class="mt-1 text-sm text-sub">登录{{ siteName }}</p>
      </div>

      <form class="mt-8 space-y-5" @submit.prevent="submit">
        <div>
          <label class="label">用户名 / 邮箱 / 手机号</label>
          <input v-model="account" class="input" placeholder="请输入账号" autocomplete="username" />
        </div>
        <div>
          <label class="label">密码</label>
          <input v-model="password" type="password" class="input" placeholder="请输入密码" autocomplete="current-password" />
        </div>
        <div v-if="error" class="text-sm text-blush bg-blush/10 rounded-lg px-4 py-2.5">{{ error }}</div>
        <button type="submit" class="btn-primary w-full" :disabled="submitting">
          {{ submitting ? '登录中…' : '登录' }}
        </button>
      </form>

      <div class="mt-6 text-center text-sm text-sub space-y-2">
        <p><RouterLink to="/forgot-password" class="text-primary-700 hover:underline">忘记密码？</RouterLink></p>
        <p>还没有账号？<RouterLink to="/register" class="text-primary-700 hover:underline">去注册</RouterLink></p>
      </div>
    </div>
  </div>
</template>