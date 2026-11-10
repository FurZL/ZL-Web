<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { cancelEventRegistration, eventCheckin, listEvents, registerEvent } from '@/api/events'
import { useDialog } from '@/composables/useDialog'
import type { EventRecord } from '@/types'

const { showToast, showConfirm } = useDialog()

const events = ref<EventRecord[]>([])
const loading = ref(true)
const error = ref('')
const acting = ref<string | null>(null)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await listEvents()
    events.value = data.items
  } catch (e) {
    error.value = e instanceof Error ? e.message : '活动加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)

const filter = ref<'all' | 'upcoming' | 'past'>('upcoming')

const filtered = computed(() => {
  const now = Date.now()
  if (filter.value === 'all') return events.value
  if (filter.value === 'upcoming') {
    return events.value.filter((e) => e.status === 'published' && (!e.ends_at || new Date(e.ends_at).getTime() >= now))
  }
  return events.value.filter((e) => e.ends_at && new Date(e.ends_at).getTime() < now)
})

async function doRegister(e: EventRecord) {
  acting.value = e.id
  try {
    await registerEvent(e.id)
    await load()
  } catch (err) {
      showToast(err instanceof Error ? err.message : '报名失败')
  } finally {
    acting.value = null
  }
}

async function doCancel(e: EventRecord) {
  if (!(await showConfirm(`确定取消报名「${e.title}」吗？`))) return
  acting.value = e.id
  try {
    await cancelEventRegistration(e.id)
    await load()
  } catch (err) {
      showToast(err instanceof Error ? err.message : '取消失败')
  } finally {
    acting.value = null
  }
}

async function doCheckin(e: EventRecord) {
  acting.value = e.id
  try {
    await eventCheckin(e.id)
    await load()
  } catch (err) {
      showToast(err instanceof Error ? err.message : '签到失败')
  } finally {
    acting.value = null
  }
}

function fmtDate(iso: string | null) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function isRegistrationOpen(e: EventRecord) {
  const now = Date.now()
  if (e.status !== 'published') return false
  if (e.registration_starts_at && now < new Date(e.registration_starts_at).getTime()) return false
  if (e.registration_ends_at && now > new Date(e.registration_ends_at).getTime()) return false
  return true
}

function isFull(e: EventRecord) {
  return e.capacity !== null && e.registered_count >= e.capacity
}

function statusLabel(e: EventRecord) {
  if (e.status === 'cancelled') return { text: '已取消', cls: 'bg-red-100 text-red-600' }
  if (e.status === 'draft') return { text: '草稿', cls: 'bg-gray-100 text-gray-500' }
  if (e.ends_at && new Date(e.ends_at).getTime() < Date.now()) return { text: '已结束', cls: 'bg-gray-100 text-gray-500' }
  if (!isRegistrationOpen(e)) return { text: '报名已截止', cls: 'bg-amber-100 text-amber-700' }
  return { text: '报名中', cls: 'bg-emerald-100 text-emerald-700' }
}

function myStatusLabel(s: string | null | undefined) {
  switch (s) {
    case 'registered': return { text: '已报名', cls: 'text-emerald-600' }
    case 'waitlisted': return { text: '候补中', cls: 'text-amber-600' }
    case 'checked_in': return { text: '已签到', cls: 'text-primary' }
    default: return null
  }
}

const tabs = [
  { key: 'upcoming', label: '即将开始' },
  { key: 'past', label: '往期活动' },
  { key: 'all', label: '全部' },
] as const
</script>

<template>
  <div class="max-w-6xl mx-auto px-4 py-10">
    <h1 class="text-3xl font-bold text-ink">活动与公告</h1>
    <p class="mt-2 text-sub">看看有什么有趣的活动，报名参加吧～</p>

    <!-- 筛选 Tab -->
    <div class="mt-6 flex gap-2">
      <button
        v-for="t in tabs"
        :key="t.key"
        class="text-sm font-medium text-primary-700 rounded-full px-5 py-2 transition"
        :class="filter === t.key ? 'bg-primary/30 border border-primary/30 shadow-glass text-primary-800' : 'bg-primary/5 border border-primary/10 hover:bg-primary/15'"
        @click="filter = t.key"
      >
        {{ t.label }}
      </button>
    </div>

    <div v-if="error" class="mt-4 text-sm text-red-600 bg-red-50 rounded-lg px-4 py-2">{{ error }}</div>

    <div v-if="loading" class="mt-10 glass-card p-12 text-center">
      <div class="spinner"></div>
      <p class="mt-3 text-sm text-sub">加载中…</p>
    </div>

    <div v-else-if="filtered.length === 0" class="mt-10 glass-card p-12 text-center">
      <div class="text-4xl">📅</div>
      <p class="mt-3 text-ink font-medium">暂无活动</p>
      <p class="mt-1 text-sm text-sub">敬请期待～</p>
    </div>

    <!-- 活动卡片 -->
    <div v-else class="mt-6 space-y-4">
      <article
        v-for="e in filtered"
        :key="e.id"
        class="glass-card p-6 hover:shadow-soft transition"
      >
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div class="flex-1 min-w-0">
            <div class="flex flex-wrap items-center gap-2">
              <h2 class="text-lg font-semibold text-ink">{{ e.title }}</h2>
              <span class="text-xs font-medium rounded-full px-2.5 py-0.5" :class="statusLabel(e).cls">
                {{ statusLabel(e).text }}
              </span>
              <span v-if="myStatusLabel(e.my_status)" class="text-xs font-medium" :class="myStatusLabel(e.my_status)!.cls">
                {{ myStatusLabel(e.my_status)!.text }}
              </span>
            </div>
            <p class="mt-1.5 text-sm text-sub leading-relaxed">{{ e.description }}</p>

            <div class="mt-3 flex flex-wrap items-center gap-4 text-xs text-faint">
              <span v-if="e.starts_at">🕐 {{ fmtDate(e.starts_at) }}</span>
              <span v-if="e.location">📍 {{ e.location }}</span>
              <span>👥 {{ e.registered_count }}<template v-if="e.capacity"> / {{ e.capacity }}</template> 人</span>
              <span v-if="e.waitlist_count" class="text-amber-600">候补 {{ e.waitlist_count }} 人</span>
            </div>
          </div>

          <!-- 操作按钮 -->
          <div class="flex items-center gap-2 shrink-0">
            <template v-if="e.my_status === 'registered' || e.my_status === 'checked_in'">
              <button
                v-if="e.my_status === 'registered'"
                class="btn-primary !px-4 !py-2 text-xs"
                :disabled="acting === e.id"
                @click="doCheckin(e)"
              >
                签到
              </button>
              <button
                class="text-xs px-4 py-2 rounded-full border border-red-200 text-red-500 hover:bg-red-50 transition"
                :disabled="acting === e.id"
                @click="doCancel(e)"
              >
                取消报名
              </button>
            </template>
            <template v-else-if="e.my_status === 'waitlisted'">
              <span class="text-xs text-amber-600 font-medium">候补中</span>
              <button
                class="text-xs px-4 py-2 rounded-full border border-red-200 text-red-500 hover:bg-red-50 transition"
                :disabled="acting === e.id"
                @click="doCancel(e)"
              >
                取消
              </button>
            </template>
            <template v-else>
              <button
                class="btn-primary !px-5 !py-2 text-xs"
                :disabled="acting === e.id || e.status !== 'published' || !isRegistrationOpen(e)"
                :class="{ 'opacity-50 cursor-not-allowed': e.status !== 'published' || !isRegistrationOpen(e) }"
                @click="doRegister(e)"
              >
                {{ acting === e.id ? '处理中…' : isFull(e) ? '加入候补' : '立即报名' }}
              </button>
            </template>
          </div>
        </div>
      </article>
    </div>
  </div>
</template>
