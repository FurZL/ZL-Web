<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
</script>

<template>
  <div class="max-w-md mx-auto px-4 py-20 text-center">
    <div class="glass-card p-10">
      <div class="w-16 h-16 mx-auto rounded-full bg-primary-50 flex items-center justify-center text-3xl">⏳</div>
      <h1 class="mt-5 text-2xl font-bold text-ink">等待管理员审批</h1>
      <p class="mt-3 text-sub leading-relaxed">
        你的注册申请已提交。管理员审批通过后，你就可以登录啦。<br />
        审批结果会尽快通知到你填写的邮箱/手机号。
      </p>
      <div class="mt-6 bg-primary-50 rounded-xl px-4 py-3 text-sm text-primary-800">
        当前状态：{{ auth.pendingApproval ? '待审批' : '已提交' }}
      </div>
      <RouterLink to="/" class="btn-ghost mt-8 inline-flex">返回首页</RouterLink>
    </div>
  </div>
</template>