<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { request } from '@/api/client'
import type { AdminUser } from '@/types'

const stats = ref({ pending: 0, total: 0 })
const loading = ref(true)

onMounted(async () => {
  try {
    const [all, pending] = await Promise.all([
      request<{ items: AdminUser[] }>({ method: 'GET', url: '/admin/users/' }),
      request<{ items: AdminUser[] }>({ method: 'GET', url: '/admin/users/pending' }),
    ])
    stats.value = { total: all.items.length, pending: pending.items.length }
  } catch {
    // 忽略统计加载失败
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div>
    <h1 class="text-2xl font-bold text-ink">仪表盘</h1>
    <p class="mt-1 text-sm text-sub">社团运营数据总览</p>

    <div class="mt-6 grid grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="glass-card p-5">
        <p class="text-xs text-faint">总用户数</p>
        <p class="mt-2 text-3xl font-bold text-ink">{{ loading ? '—' : stats.total }}</p>
      </div>
      <div class="glass-card p-5">
        <p class="text-xs text-faint">待审批</p>
        <p class="mt-2 text-3xl font-bold text-primary">{{ loading ? '—' : stats.pending }}</p>
        <RouterLink v-if="stats.pending" to="/admin/users" class="text-xs text-primary-700 hover:underline mt-1 inline-block">去审批 →</RouterLink>
      </div>
      <div class="glass-card p-5">
        <p class="text-xs text-faint">图片数</p>
        <p class="mt-2 text-3xl font-bold text-ink">—</p>
      </div>
      <div class="glass-card p-5">
        <p class="text-xs text-faint">活动报名</p>
        <p class="mt-2 text-3xl font-bold text-ink">—</p>
      </div>
    </div>

    <div class="mt-8 glass-card p-6">
      <h2 class="font-semibold text-ink">快速入口</h2>
      <div class="mt-4 grid sm:grid-cols-2 gap-3">
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