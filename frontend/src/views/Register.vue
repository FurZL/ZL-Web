<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const type = ref<'member' | 'photographer'>('member')
const form = ref({
  username: '',
  displayName: '',
  email: '',
  phone: '',
  password: '',
  reason: '',
  portfolio: '',
})

function submit() {
  auth.submitRegistration()
  router.push('/register/pending')
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
          <input v-model="form.email" class="input" placeholder="name@example.com" />
        </div>
        <div>
          <label class="label">手机号</label>
          <input v-model="form.phone" class="input" placeholder="含国家/地区码，例如 +86 138..." />
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

        <!-- 人机验证占位 -->
        <div class="flex items-center gap-3 bg-white/50 border border-primary-100 rounded-xl px-4 py-3">
          <input type="checkbox" class="w-4 h-4 accent-primary" />
          <span class="text-sm text-sub">我是人类（人机验证占位）</span>
        </div>

        <button type="submit" class="btn-primary w-full">提交注册</button>
        <p class="text-xs text-faint text-center">提交即表示同意用户协议与隐私政策</p>
      </form>
    </div>
  </div>
</template>