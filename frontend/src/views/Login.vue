<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const account = ref('')
const password = ref('')
const error = ref('')

function submit() {
  if (!account.value || !password.value) {
    error.value = '请输入账号和密码'
    return
  }
  error.value = ''
  auth.login(account.value)
  router.push('/')
}
</script>

<template>
  <div class="max-w-md mx-auto px-4 py-16">
    <div class="glass-card p-8">
      <div class="text-center">
        <span class="w-14 h-14 inline-flex items-center justify-center rounded-2xl bg-hero-gradient text-white text-2xl font-bold mx-auto">福</span>
        <h1 class="mt-4 text-2xl font-bold text-ink">欢迎回来</h1>
        <p class="mt-1 text-sm text-sub">登录浙江理工福瑞圈</p>
      </div>

      <form class="mt-8 space-y-5" @submit.prevent="submit">
        <div>
          <label class="label">用户名 / 邮箱 / 手机号</label>
          <input v-model="account" class="input" placeholder="请输入账号" />
        </div>
        <div>
          <label class="label">密码</label>
          <input v-model="password" type="password" class="input" placeholder="请输入密码" />
        </div>
        <div v-if="error" class="text-sm text-blush bg-blush/10 rounded-lg px-4 py-2.5">{{ error }}</div>
        <button type="submit" class="btn-primary w-full">登录</button>
      </form>

      <div class="mt-6 text-center text-sm text-sub space-y-2">
        <p><RouterLink to="/forgot-password" class="text-primary-700 hover:underline">忘记密码？</RouterLink></p>
        <p>还没有账号？<RouterLink to="/register" class="text-primary-700 hover:underline">去注册</RouterLink></p>
      </div>
    </div>
  </div>
</template>