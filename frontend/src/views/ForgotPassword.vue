<script setup lang="ts">
import { ref } from 'vue'

const step = ref<'identify' | 'reset'>('identify')
const target = ref('')
const code = ref('')
const newPassword = ref('')

function sendCode() {
  step.value = 'reset'
}
</script>

<template>
  <div class="max-w-md mx-auto px-4 py-16">
    <div class="glass-card p-8">
      <div class="text-center">
        <h1 class="text-2xl font-bold text-ink">找回密码</h1>
        <p class="mt-1 text-sm text-sub">通过邮箱或手机号重置密码</p>
      </div>

      <form v-if="step === 'identify'" class="mt-8 space-y-5" @submit.prevent="sendCode">
        <div>
          <label class="label">邮箱或手机号</label>
          <input v-model="target" class="input" placeholder="请输入注册时的邮箱或手机号" />
        </div>
        <button type="submit" class="btn-primary w-full">发送验证码</button>
      </form>

      <form v-else class="mt-8 space-y-5">
        <div>
          <label class="label">验证码</label>
          <input v-model="code" class="input" placeholder="请输入收到的验证码" />
        </div>
        <div>
          <label class="label">新密码</label>
          <input v-model="newPassword" type="password" class="input" placeholder="至少 8 位" />
        </div>
        <button type="submit" class="btn-primary w-full">重置密码</button>
      </form>

      <div class="mt-6 text-center text-sm text-sub">
        <RouterLink to="/login" class="text-primary-700 hover:underline">返回登录</RouterLink>
      </div>
    </div>
  </div>
</template>