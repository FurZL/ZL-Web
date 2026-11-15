<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { request } from '@/api/client'
import { useSiteConfig } from '@/composables/useSiteConfig'
import type { RegistrationConfig } from '@/types'

const router = useRouter()
const { registrationConfig } = useSiteConfig()

const type = ref<'member' | 'photographer'>('member')
const form = ref({
  username: '',
  displayName: '',
  email: '',
  phone: '',
  password: '',
  passwordConfirm: '',
  emailCode: '',
  phoneCode: '',
  reason: '',
  portfolio: '',
})

const error = ref('')
const submitting = ref(false)

const emailCooldown = ref(0)
const phoneCooldown = ref(0)

const regCfg = ref<RegistrationConfig>(registrationConfig.value)

onMounted(async () => {
  try {
    const cfg = await request<any>({ method: 'GET', url: '/site/public-config' })
    if (cfg.registration_config) regCfg.value = cfg.registration_config
  } catch { /* keep defaults */ }
  if (!regCfg.value.registration_enabled) router.replace('/')
})

function startCooldown(kind: 'email' | 'phone') {
  const cd = kind === 'email' ? emailCooldown : phoneCooldown
  cd.value = 60
  const timer = setInterval(() => {
    cd.value--
    if (cd.value <= 0) clearInterval(timer)
  }, 1000)
}

async function sendCode(kind: 'email' | 'phone') {
  const target = kind === 'email' ? form.value.email : form.value.phone
  if (!target) {
    error.value = kind === 'email' ? '请先填写邮箱' : '请先填写手机号'
    return
  }
  error.value = ''
  try {
    await request<{ dev_code?: string }>({
      method: 'POST',
      url: kind === 'email' ? '/auth/verify/email' : '/auth/verify/phone',
      data: { target, purpose: 'register' },
    })
    startCooldown(kind)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '验证码发送失败'
  }
}

async function submit() {
  error.value = ''
  if (form.value.password !== form.value.passwordConfirm) {
    error.value = '两次输入的密码不一致'
    return
  }
  if (!/[A-Z]/.test(form.value.password) || !/[a-z]/.test(form.value.password) || !/[0-9]/.test(form.value.password)) {
    error.value = '密码必须包含大写字母、小写字母和数字'
    return
  }
  submitting.value = true
  try {
    await request({
      method: 'POST',
      url: '/auth/register',
      data: {
        username: form.value.username,
        display_name: form.value.displayName,
        email: regCfg.value.require_email_verification ? form.value.email : '',
        phone: regCfg.value.require_phone_verification ? form.value.phone : '',
        password: form.value.password,
        password_confirm: form.value.passwordConfirm,
        email_code: regCfg.value.require_email_verification ? form.value.emailCode : '',
        phone_code: regCfg.value.require_phone_verification ? form.value.phoneCode : '',
        applied_role: type.value === 'photographer' ? 'photographer' : null,
        application_reason: type.value === 'photographer' ? form.value.reason : null,
        application_portfolio: type.value === 'photographer' ? form.value.portfolio : null,
      },
    })
    router.push('/register/pending')
  } catch (e) {
    error.value = e instanceof Error ? e.message : '注册失败，请重试'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="max-w-lg mx-auto px-4 py-12">
    <div class="glass-card p-8">
      <div class="text-center">
        <h1 class="text-2xl font-bold text-ink">加入我们</h1>
        <p class="mt-1 text-sm text-sub">注册并通过管理员审批后即可登录</p>
      </div>

      <div class="mt-8 grid grid-cols-2 gap-3">
        <button
          class="rounded-xl2 p-4 text-left transition border-2"
          :class="type === 'member' ? 'border-primary bg-primary-50' : 'border-white/60 bg-white/40 hover:border-primary-200'"
          @click="type = 'member'"
        >
          <p class="font-medium text-ink">普通成员</p>
          <p class="mt-1 text-xs text-sub">浏览、分享、个人空间、课表工具</p>
        </button>
        <button
          class="rounded-xl2 p-4 text-left transition border-2"
          :class="type === 'photographer' ? 'border-primary bg-primary-50' : 'border-white/60 bg-white/40 hover:border-primary-200'"
          @click="type = 'photographer'"
        >
          <p class="font-medium text-ink">摄影师</p>
          <p class="mt-1 text-xs text-sub">可上传图片到公开展示区</p>
        </button>
      </div>

      <form class="mt-8 space-y-4" @submit.prevent="submit">
        <div>
          <label class="label">用户名</label>
          <input v-model="form.username" class="input" placeholder="用于登录的唯一用户名" minlength="3" maxlength="64" required />
        </div>
        <div>
          <label class="label">昵称</label>
          <input v-model="form.displayName" class="input" placeholder="大家怎么称呼你" maxlength="64" required />
        </div>

        <div v-if="regCfg.require_email_verification">
          <label class="label">邮箱</label>
          <div class="flex gap-2">
            <input v-model="form.email" class="input flex-1" placeholder="name@example.com" type="email" autocomplete="email" required />
            <button
              type="button"
              class="btn-ghost !px-4 !py-2 whitespace-nowrap shrink-0"
              :disabled="emailCooldown > 0"
              @click="sendCode('email')"
            >
              {{ emailCooldown > 0 ? `${emailCooldown}s` : '发送验证码' }}
            </button>
          </div>
          <input v-model="form.emailCode" class="input mt-2" placeholder="邮箱验证码" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9]{6}" maxlength="6" required />
        </div>

        <div v-if="regCfg.require_phone_verification">
          <label class="label">手机号</label>
          <div class="flex gap-2">
            <input v-model="form.phone" class="input flex-1" placeholder="+86 138..." autocomplete="tel" required />
            <button
              type="button"
              class="btn-ghost !px-4 !py-2 whitespace-nowrap shrink-0"
              :disabled="phoneCooldown > 0"
              @click="sendCode('phone')"
            >
              {{ phoneCooldown > 0 ? `${phoneCooldown}s` : '发送验证码' }}
            </button>
          </div>
          <input v-model="form.phoneCode" class="input mt-2" placeholder="手机验证码" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9]{6}" maxlength="6" required />
        </div>

        <div>
          <label class="label">密码</label>
          <input v-model="form.password" type="password" class="input" placeholder="至少 8 位，含大小写字母和数字" minlength="8" maxlength="128" autocomplete="new-password" required />
        </div>
        <div>
          <label class="label">确认密码</label>
          <input v-model="form.passwordConfirm" type="password" class="input" placeholder="请再次输入密码" minlength="8" maxlength="128" autocomplete="new-password" required />
        </div>

        <template v-if="type === 'photographer'">
          <div>
            <label class="label">申请理由</label>
            <textarea v-model="form.reason" class="input min-h-[80px]" placeholder="为什么想申请摄影师？"></textarea>
          </div>
          <div>
            <label class="label">作品集链接</label>
            <input v-model="form.portfolio" class="input" placeholder="例如个人主页 / 相册链接" />
          </div>
        </template>

        <div v-if="error" class="text-sm text-blush bg-blush/10 rounded-lg px-4 py-2.5">{{ error }}</div>

        <button type="submit" class="btn-primary w-full" :disabled="submitting">
          {{ submitting ? '提交中…' : '提交注册' }}
        </button>
        <p class="text-xs text-faint text-center">提交即表示同意用户协议与隐私政策</p>
      </form>
    </div>
  </div>
</template>
