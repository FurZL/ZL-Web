<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { request } from '@/api/client'
import { useSiteConfig } from '@/composables/useSiteConfig'
import type { RegistrationConfig } from '@/types'
import SliderCaptcha from '@/components/SliderCaptcha.vue'

const LEGAL_VERSION = '2026-11-19'

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
const phoneRaw = ref('')

const emailCooldown = ref(0)
const phoneCooldown = ref(0)
const captchaShow = ref(false)
const captchaKind = ref<"email" | "phone">("email")
const agreementAccepted = ref(false)
const privacyAccepted = ref(false)

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
  cd.value = 120
  const timer = setInterval(() => {
    cd.value--
    if (cd.value <= 0) clearInterval(timer)
  }, 1000)
}

function triggerSendCode(kind: 'email' | 'phone') {
  error.value = ''
  if (kind === 'email') {
    const email = form.value.email.trim()
    if (!email) { error.value = '请先填写邮箱'; return }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { error.value = '邮箱格式不正确'; return }
    form.value.email = email
  } else {
    const raw = phoneRaw.value.trim()
    if (!raw) { error.value = '请先填写手机号'; return }
    if (!/^\d{11}$/.test(raw)) { error.value = '手机号格式不正确，请输入 11 位数字'; return }
    form.value.phone = raw
  }
  captchaKind.value = kind
  captchaShow.value = true
}

async function onCaptchaVerified(verificationToken: string) {
  captchaShow.value = false
  const kind = captchaKind.value
  const target = kind === 'email' ? form.value.email : form.value.phone
  try {
    await request<{ dev_code?: string }>({
      method: 'POST',
      url: kind === 'email' ? '/auth/verify/email' : '/auth/verify/phone',
      data: { target, purpose: 'register', verification_token: verificationToken },
    })
    startCooldown(kind)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '验证码发送失败'
  }
}
async function submit() {
  error.value = ''
  if (!agreementAccepted.value || !privacyAccepted.value) {
    error.value = '请先阅读并勾选同意用户协议和隐私政策'
    return
  }
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
        phone: regCfg.value.require_phone_verification ? (form.value.phone || phoneRaw.value) : '',
        password: form.value.password,
        password_confirm: form.value.passwordConfirm,
        email_code: regCfg.value.require_email_verification ? form.value.emailCode : '',
        phone_code: regCfg.value.require_phone_verification ? form.value.phoneCode : '',
        applied_role: type.value === 'photographer' ? 'photographer' : null,
        application_reason: type.value === 'photographer' ? form.value.reason : null,
        application_portfolio: type.value === 'photographer' ? form.value.portfolio : null,
        terms_accepted: agreementAccepted.value,
        privacy_accepted: privacyAccepted.value,
        terms_version: LEGAL_VERSION,
        privacy_version: LEGAL_VERSION,
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

      <form class="mt-8 space-y-4" novalidate @submit.prevent="submit">
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
              @click="triggerSendCode('email')"
            >
              {{ emailCooldown > 0 ? `${emailCooldown}s` : '发送验证码' }}
            </button>
          </div>
          <input v-model="form.emailCode" class="input mt-2" placeholder="邮箱验证码" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9]{6}" maxlength="6" required />
        </div>

        <div v-if="regCfg.require_phone_verification">
          <label class="label">手机号</label>
          <div class="flex gap-2">
            <div class="flex items-center input flex-1 !p-0 overflow-hidden">
              <span class="shrink-0 bg-ink/5 text-sub text-sm px-3 py-2 select-none">+86</span>
              <input v-model="phoneRaw" class="flex-1 border-none bg-transparent px-3 py-2 text-sm outline-none" placeholder="输入 11 位手机号" maxlength="11" inputmode="numeric" autocomplete="tel" required />
            </div>
            <button
              type="button"
              class="btn-ghost !px-4 !py-2 whitespace-nowrap shrink-0"
              :disabled="phoneCooldown > 0"
              @click="triggerSendCode('phone')"
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

        <div class="space-y-2.5 rounded-lg bg-white/40 px-4 py-3.5">
          <label class="flex items-start gap-2.5 text-xs leading-5 text-sub cursor-pointer">
            <input
              v-model="agreementAccepted"
              type="checkbox"
              class="mt-0.5 h-4 w-4 shrink-0 rounded border-ink/20 text-primary focus:ring-primary/30"
            />
            <span>
              我已阅读并同意
              <RouterLink to="/legal/terms" target="_blank" class="text-primary-700 hover:underline">《用户协议》</RouterLink>
            </span>
          </label>
          <label class="flex items-start gap-2.5 text-xs leading-5 text-sub cursor-pointer">
            <input
              v-model="privacyAccepted"
              type="checkbox"
              class="mt-0.5 h-4 w-4 shrink-0 rounded border-ink/20 text-primary focus:ring-primary/30"
            />
            <span>
              我已阅读并同意
              <RouterLink to="/legal/privacy" target="_blank" class="text-primary-700 hover:underline">《隐私政策》</RouterLink>
              ，包括其中的第三方服务说明
            </span>
          </label>
        </div>

        <div v-if="error" class="text-sm text-blush bg-blush/10 rounded-lg px-4 py-2.5">{{ error }}</div>

        <button type="submit" class="btn-primary w-full" :disabled="submitting">
          {{ submitting ? '提交中…' : '提交注册' }}
        </button>
      </form>
    </div>
  </div>
  <SliderCaptcha :show="captchaShow" @close="captchaShow = false" @verified="onCaptchaVerified" />
</template>
