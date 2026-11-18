<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SliderCaptcha from '@/components/SliderCaptcha.vue'
import { bindQqWithAccount, exchangeQqCallback } from '@/api/oauth'
import { useAuthStore } from '@/stores/auth'
import type { OauthProvidedUser } from '@/types'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const status = ref<'loading' | 'bind' | 'error'>('loading')
const error = ref('')
const nickname = ref('QQ用户')
const oauthToken = ref('')
const returnTo = ref('')
const account = ref('')
const password = ref('')
const captchaShow = ref(false)

function finishSession(accessToken: string, user: OauthProvidedUser) {
  auth.setSession(accessToken, {
    id: user.id,
    username: user.username,
    display_name: user.display_name,
    role: user.role,
    avatar_url: user.avatar_url,
    bio: user.bio,
  })
}

async function handleCallback() {
  const code = route.query.code
  const state = route.query.state
  if (typeof code !== 'string' || typeof state !== 'string') {
    status.value = 'error'
    error.value = 'QQ 回调参数缺失，请重新登录'
    return
  }
  try {
    const data = await exchangeQqCallback(code, state)
    if (data.bound && data.access_token && data.user) {
      finishSession(data.access_token, data.user)
      router.replace(returnTo.value || '/')
      return
    }
    if (!data.bound && data.oauth_token) {
      oauthToken.value = data.oauth_token
      returnTo.value = data.return_to ?? ''
      nickname.value = data.nickname || 'QQ用户'
      status.value = 'bind'
      return
    }
    status.value = 'error'
    error.value = 'QQ 登录状态无法识别'
  } catch (e) {
    status.value = 'error'
    error.value = e instanceof Error ? e.message : 'QQ 登录失败'
  }
}

function triggerBind() {
  if (!account.value || !password.value) {
    error.value = '请输入账号和密码'
    return
  }
  error.value = ''
  captchaShow.value = true
}

function closeCaptcha() {
  captchaShow.value = false
}

async function onCaptchaVerified(token: string) {
  captchaShow.value = false
  try {
    const data = await bindQqWithAccount(oauthToken.value, account.value, password.value, token)
    if (data.bound && data.access_token && data.user) {
      finishSession(data.access_token, data.user)
      router.replace(returnTo.value || '/')
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : '绑定失败'
  }
}

onMounted(handleCallback)
</script>

<template>
  <div class="max-w-md mx-auto px-4 py-16">
    <div class="glass-card p-8">
      <div v-if="status === 'loading'" class="text-center">
        <div class="spinner mx-auto"></div>
        <p class="mt-3 text-sm text-sub">正在完成 QQ 登录…</p>
      </div>

      <div v-else-if="status === 'error'" class="text-center">
        <p class="text-blush">{{ error }}</p>
        <button class="btn-primary mt-5" @click="router.push('/login')">返回登录</button>
      </div>

      <div v-else>
        <div class="text-center">
          <h1 class="text-xl font-bold text-ink">绑定已有账号</h1>
          <p class="mt-1 text-sm text-sub">QQ 账号：{{ nickname }}</p>
        </div>

        <form class="mt-7 space-y-5" @submit.prevent="triggerBind">
          <div>
            <label class="label">用户名 / 邮箱 / 手机号</label>
            <input v-model="account" class="input" autocomplete="username" />
          </div>
          <div>
            <label class="label">密码</label>
            <input v-model="password" type="password" class="input" autocomplete="current-password" />
          </div>
          <div v-if="error" class="text-sm text-blush bg-blush/10 rounded-lg px-4 py-2.5">{{ error }}</div>
          <button type="submit" class="btn-primary w-full">完成绑定并登录</button>
        </form>

        <div class="mt-5 text-center text-sm text-sub">
          <p>还没有本站账号？<RouterLink to="/register" class="text-primary-700 hover:underline">去注册</RouterLink></p>
          <p class="mt-2 text-xs">注册并审批通过后，可在个人主页绑定这个 QQ</p>
        </div>
      </div>
    </div>
  </div>
  <SliderCaptcha :show="captchaShow" @close="closeCaptcha" @verified="onCaptchaVerified" />
</template>
