<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { request } from '@/api/client'
import UserAvatar from '@/components/UserAvatar.vue'
import type { AdminUser } from '@/types'

const tab = ref<'pending' | 'all'>('pending')
const users = ref<AdminUser[]>([])
const pending = ref<AdminUser[]>([])
const loading = ref(false)
const error = ref('')
const acting = ref<string | null>(null)

const shown = computed(() => (tab.value === 'pending' ? pending.value : users.value))

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [a, p] = await Promise.all([
      request<{ items: AdminUser[] }>({ method: 'GET', url: '/admin/users/' }),
      request<{ items: AdminUser[] }>({ method: 'GET', url: '/admin/users/pending' }),
    ])
    users.value = a.items
    pending.value = p.items
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function approve(id: string) {
  acting.value = id
  error.value = ''
  try {
    await request({ method: 'POST', url: `/admin/users/${id}/approve` })
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '审批失败'
  } finally {
    acting.value = null
  }
}

async function reject(id: string) {
  acting.value = id
  error.value = ''
  try {
    await request({ method: 'POST', url: `/admin/users/${id}/reject` })
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '操作失败'
  } finally {
    acting.value = null
  }
}

function fmtDate(s: string) {
  if (!s) return ''
  return s.slice(0, 10)
}

const roleLabel: Record<string, string> = {
  member: '成员',
  photographer: '摄影师',
  moderator: '审核员',
  admin: '管理员',
  super_admin: '超级管理员',
}

onMounted(load)
</script>

<template>
  <div>
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold text-ink">用户管理</h1>
      <span v-if="pending.length" class="text-sm font-medium text-primary-700 bg-primary-50 rounded-full px-3 py-1">
        {{ pending.length }} 人待审批
      </span>
    </div>

    <!-- Tab 切换 -->
    <div class="mt-6 flex gap-2">
      <button
        class="px-4 py-1.5 rounded-full text-sm transition"
        :class="tab === 'pending' ? 'bg-primary text-white shadow-glow' : 'bg-white/70 text-sub hover:bg-primary-50'"
        @click="tab = 'pending'"
      >
        待审批
      </button>
      <button
        class="px-4 py-1.5 rounded-full text-sm transition"
        :class="tab === 'all' ? 'bg-primary text-white shadow-glow' : 'bg-white/70 text-sub hover:bg-primary-50'"
        @click="tab = 'all'"
      >
        全部用户
      </button>
    </div>

    <div v-if="error" class="mt-4 text-sm text-blush bg-blush/10 rounded-lg px-4 py-2.5">{{ error }}</div>

    <div v-if="loading" class="mt-10 text-center text-sub">加载中…</div>

    <!-- 空状态 -->
    <div v-else-if="!shown.length" class="mt-10 glass-card p-12 text-center">
      <div class="text-4xl">🎉</div>
      <p class="mt-3 text-ink font-medium">
        {{ tab === 'pending' ? '没有待审批的用户' : '还没有用户' }}
      </p>
      <p class="mt-1 text-sm text-sub">{{ tab === 'pending' ? '所有注册申请都已处理完毕' : '' }}</p>
    </div>

    <!-- 用户列表 -->
    <div v-else class="mt-6 space-y-3">
      <div v-for="u in shown" :key="u.id" class="glass-card p-5">
        <div class="flex items-start gap-4">
          <UserAvatar :name="u.display_name || u.username" :size="48" />
          <div class="flex-1 min-w-0">
            <div class="flex flex-wrap items-center gap-2">
              <span class="font-semibold text-ink">{{ u.display_name }}</span>
              <span class="text-xs text-faint">@{{ u.username }}</span>
              <span v-if="u.applied_role" class="text-xs font-medium text-blush bg-blush/10 rounded-full px-2.5 py-0.5">
                申请摄影师
              </span>
              <span class="text-xs text-primary-700 bg-primary-50 rounded-full px-2.5 py-0.5">
                {{ roleLabel[u.role] ?? u.role }}
              </span>
            </div>
            <div class="mt-1 text-sm text-sub">
              {{ u.email }} · 注册于 {{ fmtDate(u.created_at) }}
            </div>
            <!-- 摄影师申请详情 -->
            <div v-if="u.applied_role === 'photographer'" class="mt-3 space-y-1.5 bg-primary-50/50 rounded-lg p-3 text-sm">
              <p v-if="u.application_reason" class="text-sub">
                <span class="text-ink font-medium">申请理由：</span>{{ u.application_reason }}
              </p>
              <p v-if="u.application_portfolio" class="text-sub">
                <span class="text-ink font-medium">作品集：</span>
                <a :href="u.application_portfolio" target="_blank" class="text-primary-700 hover:underline" rel="noopener">
                  {{ u.application_portfolio }}
                </a>
              </p>
            </div>
          </div>
          <div v-if="tab === 'pending'" class="flex gap-2 shrink-0">
            <button
              class="btn-primary !px-4 !py-1.5 text-xs"
              :disabled="acting === u.id"
              @click="approve(u.id)"
            >
              {{ acting === u.id ? '处理中…' : '通过' }}
            </button>
            <button
              class="btn-ghost !px-4 !py-1.5 text-xs !text-blush !border-blush/40"
              :disabled="acting === u.id"
              @click="reject(u.id)"
            >
              拒绝
            </button>
          </div>
          <span v-else class="text-xs shrink-0 font-medium rounded-full px-2.5 py-0.5" :class="u.status === 'active' ? 'text-emerald-700 bg-emerald-50' : 'text-faint bg-neutral-100'">
            {{ u.status === 'active' ? '已激活' : u.status }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>