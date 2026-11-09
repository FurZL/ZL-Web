<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { request } from '@/api/client'

const router = useRouter()

const type = ref<'member' | 'photographer'>('member')
const form = ref({
  username: '',
  displayName: '',
  email: '',
  phone: '',
  password: '',
  emailCode: '',
  phoneCode: '',
  reason: '',
  portfolio: '',
})

const error = ref('')
const submitting = ref(false)
const sendingEmail = ref(false)
const sendingPhone = ref(false)
const sentEmail = ref(false)
const sentPhone = ref(false)

async function sendCode(kind: 'email' | 'phone') {
  const target = kind === 'email' ? form.value.email : form.value.phone
  if (!target) {
    error.value = kind === 'email' ? '请先填写邮箱' : '请先填写手机号'
    return
  }
  error.value = ''
  if (kind === 'email') sendingEmail.value = true
  else sendingPhone.value = true
  try {
    const res = await request<{ dev_code?: string }>({
      method: 'POST',
      url: kind === 'email' ? '/auth/verify/email' : '/auth/verify/phone',
      data: { target, purpose: 'register' },
    })
    if (kind === 'email') {
      sentEmail.value = true
      if (res.dev_code) form.value.emailCode = res.dev_code
    } else {
      sentPhone.value = true
      if (res.dev_code) form.value.phoneCode = res.dev_code
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : '验证码发送失败'
  } finally {
    if (kind === 'email') sendingEmail.value = false
    else sendingPhone.value = false
  }
}

async function submit() {
  error.value = ''
  submitting.value = true
  try {
    await request({
      method: 'POST',
      url: '/auth/register',
      data: {
        username: form.value.username,
        display_name: form.value.displayName,
        email: form.value.email,
        phone: form.value.phone,
        password: form.value.password,
        email_code: form.value.emailCode,
        phone_code: form.value.phoneCode,
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

      <!-- 类型选择 -->
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
          <input v-model="form.username" class="input" placeholder="用于登录的唯一用户名" />
        </div>
        <div>
          <label class="label">昵称</label>
          <input v-model="form.displayName" class="input" placeholder="大家怎么称呼你" />
        </div>

        <div>
          <label class="label">邮箱</label>
          <div class="flex gap-2">
            <input v-model="form.email" class="input flex-1" placeholder="name@example.com" type="email" />
            <button type="button" class="btn-ghost !px-4 !py-2 whitespace-nowrap shrink-0" :disabled="sendingEmail" @click="sendCode('email')">
              {{ sendingEmail ? '发送中…' : sentEmail ? '重新发送' : '发送验证码' }}
            </button>
          </div>
          <input v-model="form.emailCode" class="input mt-2" placeholder="邮箱验证码" />
        </div>

        <div>
          <label class="label">手机号</label>
          <div class="flex gap-2">
            <input v-model="form.phone" class="input flex-1" placeholder="+86 138..." />
            <button type="button" class="btn-ghost !px-4 !py-2 whitespace-nowrap shrink-0" :disabled="sendingPhone" @click="sendCode('phone')">
              {{ sendingPhone ? '发送中…' : sentPhone ? '重新发送' : '发送验证码' }}
            </button>
          </div>
          <input v-model="form.phoneCode" class="input mt-2" placeholder="手机验证码" />
        </div>

        <div>
          <label class="label">密码</label>
          <input v-model="form.password" type="password" class="input" placeholder="至少 8 位" />
        </div>

        <!-- 摄影师额外字段 -->
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