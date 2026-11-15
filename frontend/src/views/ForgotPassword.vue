<script setup lang="ts">

import { ref } from 'vue'
import { useRouter } from 'vue-router'
import SliderCaptcha from '@/components/SliderCaptcha.vue'
import { request } from '@/api/client'

const router = useRouter()
const step = ref<'identify' | 'reset'>('identify')
const target = ref('')
const code = ref('')
const newPassword = ref('')
const newPasswordConfirm = ref('')
const error = ref('')
const submitting = ref(false)
const cooldown = ref(0)
const captchaShow = ref(false)
let captchaVerifyToken = ''

function triggerSendCode() {
  error.value = ''
  const v = target.value.trim()
  if (!v) { error.value = '请填写邮箱或手机号'; return }
  target.value = v
  const isEmail = /@/.test(v)
  if (isEmail) {
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)) { error.value = '邮箱格式不正确'; return }
  } else {
    if (!/^\d{11}$/.test(v)) { error.value = '手机号格式不正确，请输入 11 位数字'; return }
  }
  captchaShow.value = true
}

async function onCaptchaVerified(token: string) {
  captchaShow.value = false
  captchaVerifyToken = token
  await doSendCode()
}

async function doSendCode() {
  const t = target.value
  if (!t) {
    error.value = '请填写邮箱或手机号'
    return
  }
  error.value = ''
  const isEmail = /@/.test(t)
  try {
    await request<{ dev_code?: string }>({
      method: 'POST',
      url: isEmail ? '/auth/verify/email' : '/auth/verify/phone',
      data: { target: t, purpose: 'password_reset', verification_token: captchaVerifyToken },
    })
    cooldown.value = 120
    const timer = setInterval(() => {
      cooldown.value--
      if (cooldown.value <= 0) clearInterval(timer)
    }, 1000)
    step.value = 'reset'
  } catch (e) {
    error.value = e instanceof Error ? e.message : '验证码发送失败'
  }
}

async function reset() {
  error.value = ''
  if (newPassword.value !== newPasswordConfirm.value) {
    error.value = '两次输入的密码不一致'
    return
  }
  if (!/[A-Z]/.test(newPassword.value) || !/[a-z]/.test(newPassword.value) || !/[0-9]/.test(newPassword.value)) {
    error.value = '密码必须包含大写字母、小写字母和数字'
    return
  }
  submitting.value = true
  try {
    await request({
      method: 'POST',
      url: '/auth/password/reset',
      data: {
        target: target.value,
        code: code.value,
        new_password: newPassword.value,
        new_password_confirm: newPasswordConfirm.value,
      },
    })
    router.push('/login')
  } catch (e) {
    error.value = e instanceof Error ? e.message : '重置密码失败'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="max-w-md mx-auto px-4 py-16">
    <div class="glass-card p-8">
      <div class="text-center">
        <h1 class="text-2xl font-bold text-ink">找回密码</h1>
        <p class="mt-1 text-sm text-sub">通过邮箱或手机号重置密码</p>
      </div>

      <form v-if="step === 'identify'" class="mt-8 space-y-5" @submit.prevent="triggerSendCode">
        <div>
          <label class="label">邮箱或手机号</label>
          <input v-model="target" class="input" placeholder="请输入注册时的邮箱或手机号" />
        </div>
        <div v-if="error" class="text-sm text-blush bg-blush/10 rounded-lg px-4 py-2.5">{{ error }}</div>
        <button type="submit" class="btn-primary w-full" :disabled="cooldown > 0">
          {{ cooldown > 0 ? `${cooldown}s 后可重新发送` : '发送验证码' }}
        </button>
      </form>

      <form v-else class="mt-8 space-y-5" @submit.prevent="reset">
        <div>
          <label class="label">验证码</label>
          <input v-model="code" class="input" placeholder="请输入收到的验证码" />
        </div>
        <div>
          <label class="label">新密码</label>
          <input v-model="newPassword" type="password" class="input" placeholder="至少 8 位，含大小写字母和数字" />
        </div>
        <div>
          <label class="label">确认新密码</label>
          <input v-model="newPasswordConfirm" type="password" class="input" placeholder="请再次输入新密码" />
        </div>
        <div v-if="error" class="text-sm text-blush bg-blush/10 rounded-lg px-4 py-2.5">{{ error }}</div>
        <div class="flex gap-3">
          <button type="button" class="btn-ghost flex-1" @click="triggerSendCode" :disabled="cooldown > 0">
            {{ cooldown > 0 ? `${cooldown}s` : '重新发送验证码' }}
          </button>
          <button type="submit" class="btn-primary flex-1" :disabled="submitting">
            {{ submitting ? '重置中…' : '重置密码' }}
          </button>
        </div>
      </form>

      <div class="mt-6 text-center text-sm text-sub">
        <RouterLink to="/login" class="text-primary-700 hover:underline">返回登录</RouterLink>
      </div>
    </div>
  </div>
  <SliderCaptcha :show="captchaShow" @close="captchaShow = false" @verified="onCaptchaVerified" />
</template>