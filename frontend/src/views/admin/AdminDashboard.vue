<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { request } from '@/api/client'
const stats = ref<{ users: number; pending_users: number; images: number; registrations: number; open_reports: number } | null>(null)
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    stats.value = await request({ method: 'GET', url: '/admin/dashboard/overview' })
  } catch (e) {
    error.value = e instanceof Error ? e.message : '统计加载失败'
  } finally {
    loading.value = false
  }
}
onMounted(load)
</script>

<template>
  <div>
    <h1 class="text-2xl font-bold text-ink">仪表盘</h1>
    <p class="mt-1 text-sm text-sub">社团运营数据总览</p>
    <div v-if="error" role="alert" class="mt-4 text-sm text-red-600">{{ error }} <button class="underline" @click="load">重试</button></div>

    <div class="mt-6 grid grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="glass-card p-5">
        <p class="text-xs text-faint">总用户数</p>
        <p class="mt-2 text-3xl font-bold text-ink">{{ loading ? '—' : stats?.users ?? '—' }}</p>
      </div>
      <div class="glass-card p-5">
        <p class="text-xs text-faint">待审批</p>
        <p class="mt-2 text-3xl font-bold text-primary">{{ loading ? '—' : stats?.pending_users ?? '—' }}</p>
        <RouterLink v-if="stats?.pending_users" to="/admin/users" class="text-xs text-primary-700 hover:underline mt-1 inline-block">去审批 →</RouterLink>
      </div>
      <div class="glass-card p-5">
        <p class="text-xs text-faint">图片数</p>
        <p class="mt-2 text-3xl font-bold text-ink">{{ loading ? '—' : stats?.images ?? '—' }}</p>
      </div>
      <div class="glass-card p-5">
        <p class="text-xs text-faint">活动报名</p>
        <p class="mt-2 text-3xl font-bold text-ink">{{ loading ? '—' : stats?.registrations ?? '—' }}</p>
      </div>
    </div>

    <div class="mt-8 glass-card p-6">
      <h2 class="font-semibold text-ink">快速入口</h2>
      <div class="mt-4 grid sm:grid-cols-2 gap-3">
        <RouterLink to="/admin/images?view=reports" class="flex items-center gap-3 p-4 rounded-xl bg-primary-50 hover:bg-primary-100 transition">
          <div><p class="text-sm font-medium text-ink">图片举报 <span v-if="stats?.open_reports">({{ stats.open_reports }} 待处理)</span></p></div>
        </RouterLink>
        <RouterLink to="/admin/users" class="flex items-center gap-3 p-4 rounded-xl bg-primary-50 hover:bg-primary-100 transition">
          <span class="text-2xl">👥</span>
          <div>
            <p class="text-sm font-medium text-ink">用户审批</p>
            <p class="text-xs text-sub">处理新成员注册申请</p>
          </div>
        </RouterLink>
        <RouterLink to="/admin/settings" class="flex items-center gap-3 p-4 rounded-xl bg-primary-50 hover:bg-primary-100 transition">
          <span class="text-2xl">⚙️</span>
          <div>
            <p class="text-sm font-medium text-ink">网站设置</p>
            <p class="text-xs text-sub">修改社团介绍、页脚信息</p>
          </div>
        </RouterLink>
      </div>
    </div>
  </div>
</template>
