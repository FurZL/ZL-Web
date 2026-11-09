<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  adminCheckin,
  adminCreateEvent,
  adminDeleteEvent,
  adminGetEventDetail,
  adminListEvents,
  adminSetEventStatus,
  adminUpdateEvent,
} from '@/api/events'
import type { EventRecord, EventRegistration } from '@/types'

const events = ref<EventRecord[]>([])
const loading = ref(true)
const error = ref('')
const saving = ref(false)

// 创建/编辑弹窗
const showForm = ref(false)
const editingId = ref<string | null>(null)
const form = reactive({
  title: '',
  description: '',
  location: '',
  starts_at: '',
  ends_at: '',
  capacity: '' as string | number,
  registration_starts_at: '',
  registration_ends_at: '',
  publish_now: true,
})

// 详情/报名管理弹窗
const showDetail = ref(false)
const detailEvent = ref<EventRecord | null>(null)
const detailRegs = ref<EventRegistration[]>([])
const detailLoading = ref(false)
const actingId = ref<string | null>(null)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await adminListEvents()
    events.value = data.items
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)

function openCreate() {
  editingId.value = null
  form.title = ''
  form.description = ''
  form.location = ''
  form.starts_at = ''
  form.ends_at = ''
  form.capacity = ''
  form.registration_starts_at = ''
  form.registration_ends_at = ''
  form.publish_now = true
  showForm.value = true
}

function openEdit(e: EventRecord) {
  editingId.value = e.id
  form.title = e.title
  form.description = e.description ?? ''
  form.location = e.location ?? ''
  form.starts_at = e.starts_at ? e.starts_at.slice(0, 16) : ''
  form.ends_at = e.ends_at ? e.ends_at.slice(0, 16) : ''
  form.capacity = e.capacity ?? ''
  form.registration_starts_at = e.registration_starts_at ? e.registration_starts_at.slice(0, 16) : ''
  form.registration_ends_at = e.registration_ends_at ? e.registration_ends_at.slice(0, 16) : ''
  form.publish_now = e.status === 'published'
  showForm.value = true
}

function closeForm() {
  showForm.value = false
  editingId.value = null
}

async function save() {
  if (!form.title.trim() || !form.starts_at || !form.ends_at) {
    error.value = '标题和起止时间不能为空'
    return
  }
  saving.value = true
  error.value = ''
  try {
    const payload = {
      title: form.title,
      description: form.description || null,
      location: form.location || null,
      starts_at: new Date(form.starts_at).toISOString(),
      ends_at: new Date(form.ends_at).toISOString(),
      capacity: form.capacity ? Number(form.capacity) : null,
      registration_starts_at: form.registration_starts_at
        ? new Date(form.registration_starts_at).toISOString()
        : null,
      registration_ends_at: form.registration_ends_at
        ? new Date(form.registration_ends_at).toISOString()
        : null,
    }
    if (editingId.value) {
      await adminUpdateEvent(editingId.value, payload)
    } else {
      await adminCreateEvent({ ...payload, publish_now: form.publish_now })
    }
    closeForm()
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '保存失败'
  } finally {
    saving.value = false
  }
}

async function toggleStatus(e: EventRecord) {
  const next = e.status === 'published' ? 'draft' : 'published'
  try {
    await adminSetEventStatus(e.id, next)
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '操作失败'
  }
}

async function cancelEvent(e: EventRecord) {
  if (!confirm(`确定取消活动「${e.title}」吗？`)) return
  try {
    await adminSetEventStatus(e.id, 'cancelled')
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '操作失败'
  }
}

async function removeEvent(e: EventRecord) {
  if (!confirm(`确定删除活动「${e.title}」吗？此操作不可恢复。`)) return
  try {
    await adminDeleteEvent(e.id)
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '删除失败'
  }
}

async function openDetail(e: EventRecord) {
  detailEvent.value = e
  detailLoading.value = true
  showDetail.value = true
  try {
    const data = await adminGetEventDetail(e.id)
    detailEvent.value = data.event
    detailRegs.value = data.items
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载详情失败'
  } finally {
    detailLoading.value = false
  }
}

function closeDetail() {
  showDetail.value = false
  detailEvent.value = null
  detailRegs.value = []
}

async function doCheckin(reg: EventRegistration) {
  if (!detailEvent.value) return
  actingId.value = reg.id
  try {
    await adminCheckin(detailEvent.value.id, reg.id)
    await openDetail(detailEvent.value)
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '签到失败'
  } finally {
    actingId.value = null
  }
}

const regStatus = computed(() => {
  const map: Record<string, { text: string; cls: string }> = {
    registered: { text: '已报名', cls: 'bg-emerald-100 text-emerald-700' },
    waitlisted: { text: '候补', cls: 'bg-amber-100 text-amber-700' },
    cancelled: { text: '已取消', cls: 'bg-gray-100 text-gray-500' },
    checked_in: { text: '已签到', cls: 'bg-primary-100 text-primary-700' },
  }
  return map
})

function fmtDate(iso: string | null) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const eventStatus: Record<string, { text: string; cls: string }> = {
  draft: { text: '草稿', cls: 'bg-gray-100 text-gray-600' },
  published: { text: '已发布', cls: 'bg-emerald-100 text-emerald-700' },
  cancelled: { text: '已取消', cls: 'bg-red-100 text-red-600' },
}

const sortedEvents = computed(() =>
  [...events.value].sort((a, b) => (b.starts_at ?? '').localeCompare(a.starts_at ?? '')),
)

const registeredList = computed(() => detailRegs.value.filter((r) => r.status !== 'cancelled'))
</script>

<template>
  <div>
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-ink">活动管理</h1>
        <p class="mt-1 text-sm text-sub">创建、编辑、发布活动，管理报名与签到</p>
      </div>
      <button class="btn-primary" @click="openCreate">+ 新建活动</button>
    </div>

    <div v-if="error && !showForm && !showDetail" class="mt-4 text-sm text-red-600 bg-red-50 rounded-lg px-4 py-2">
      {{ error }}
    </div>

    <div v-if="loading" class="mt-8 glass-card p-12 text-center">
      <div class="w-8 h-8 border-4 border-primary-200 border-t-primary rounded-full animate-spin mx-auto"></div>
      <p class="mt-3 text-sm text-sub">加载中…</p>
    </div>

    <div v-else-if="sortedEvents.length === 0" class="mt-8 glass-card p-12 text-center">
      <div class="text-4xl">📅</div>
      <p class="mt-3 text-ink font-medium">还没有活动</p>
      <p class="mt-1 text-sm text-sub">点击右上角「新建活动」创建第一条吧</p>
    </div>

    <div v-else class="mt-6 space-y-3">
      <div
        v-for="e in sortedEvents"
        :key="e.id"
        class="glass-card p-5 flex flex-col sm:flex-row sm:items-center gap-3"
      >
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <h3 class="font-semibold text-ink truncate">{{ e.title }}</h3>
            <span
              class="text-xs font-medium rounded-full px-2.5 py-0.5"
              :class="eventStatus[e.status]?.cls ?? 'bg-gray-100 text-gray-600'"
            >
              {{ eventStatus[e.status]?.text ?? e.status }}
            </span>
          </div>
          <div class="mt-1.5 flex flex-wrap items-center gap-3 text-xs text-faint">
            <span>🕐 {{ fmtDate(e.starts_at) }}</span>
            <span v-if="e.location">📍 {{ e.location }}</span>
            <span>👥 {{ e.registered_count }}<template v-if="e.capacity"> / {{ e.capacity }}</template> 人</span>
            <span v-if="e.waitlist_count" class="text-amber-600">候补 {{ e.waitlist_count }}</span>
          </div>
        </div>
        <div class="flex items-center gap-2 shrink-0 flex-wrap">
          <button class="text-xs px-3 py-1.5 rounded-lg border border-primary-200 text-primary-700 hover:bg-primary-50 transition" @click="openDetail(e)">
            报名/签到
          </button>
          <button class="text-xs px-3 py-1.5 rounded-lg border border-gray-200 text-faint hover:border-primary-200 transition" @click="openEdit(e)">
            编辑
          </button>
          <button
            class="text-xs px-3 py-1.5 rounded-lg border transition"
            :class="e.status === 'published' ? 'border-amber-200 text-amber-600 hover:bg-amber-50' : 'border-emerald-200 text-emerald-600 hover:bg-emerald-50'"
            @click="toggleStatus(e)"
          >
            {{ e.status === 'published' ? '下架' : '发布' }}
          </button>
          <button
            v-if="e.status !== 'cancelled'"
            class="text-xs px-3 py-1.5 rounded-lg border border-red-200 text-red-500 hover:bg-red-50 transition"
            @click="cancelEvent(e)"
          >
            取消
          </button>
          <button
            class="text-xs px-3 py-1.5 rounded-lg border border-gray-200 text-red-500 hover:border-red-300 transition"
            @click="removeEvent(e)"
          >
            删除
          </button>
        </div>
      </div>
    </div>

    <!-- 创建/编辑弹窗 -->
    <div v-if="showForm" class="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4" @click.self="closeForm">
      <div class="glass-card p-6 w-full max-w-lg max-h-[85vh] overflow-auto">
        <h2 class="text-lg font-bold text-ink">{{ editingId ? '编辑活动' : '新建活动' }}</h2>
        <div v-if="error && showForm" class="mt-3 text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{{ error }}</div>
        <div class="mt-4 space-y-4">
          <div>
            <label class="label">活动标题</label>
            <input v-model="form.title" class="input" placeholder="活动标题" />
          </div>
          <div>
            <label class="label">描述</label>
            <textarea v-model="form.description" class="input min-h-[80px]" rows="3" placeholder="活动描述…"></textarea>
          </div>
          <div>
            <label class="label">地点</label>
            <input v-model="form.location" class="input" placeholder="活动地点" />
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="label">开始时间</label>
              <input v-model="form.starts_at" type="datetime-local" class="input" />
            </div>
            <div>
              <label class="label">结束时间</label>
              <input v-model="form.ends_at" type="datetime-local" class="input" />
            </div>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="label">报名开始（可选）</label>
              <input v-model="form.registration_starts_at" type="datetime-local" class="input" />
            </div>
            <div>
              <label class="label">报名截止（可选）</label>
              <input v-model="form.registration_ends_at" type="datetime-local" class="input" />
            </div>
          </div>
          <div>
            <label class="label">人数上限（留空不限）</label>
            <input v-model="form.capacity" type="number" class="input" placeholder="不限" min="1" />
          </div>
          <label v-if="!editingId" class="flex items-center gap-2 text-sm text-sub cursor-pointer">
            <input v-model="form.publish_now" type="checkbox" class="accent-primary" />
            立即发布
          </label>
        </div>
        <div class="mt-6 flex gap-3">
          <button class="btn-ghost flex-1" @click="closeForm">取消</button>
          <button class="btn-primary flex-1" :disabled="saving" @click="save">
            {{ saving ? '保存中…' : '保存' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 报名/签到详情弹窗 -->
    <div v-if="showDetail" class="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4" @click.self="closeDetail">
      <div class="glass-card p-6 w-full max-w-xl max-h-[85vh] overflow-auto">
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-bold text-ink">{{ detailEvent?.title }} — 报名管理</h2>
          <button class="text-sm text-faint hover:text-ink transition" @click="closeDetail">✕</button>
        </div>

        <div v-if="detailLoading" class="mt-6 text-center py-8">
          <div class="w-8 h-8 border-4 border-primary-200 border-t-primary rounded-full animate-spin mx-auto"></div>
          <p class="mt-3 text-sm text-sub">加载中…</p>
        </div>

        <template v-else>
          <div class="mt-4 flex flex-wrap gap-4 text-sm text-sub">
            <span>👥 正式报名 {{ detailEvent?.registered_count }}<template v-if="detailEvent?.capacity"> / {{ detailEvent?.capacity }}</template> 人</span>
            <span v-if="detailEvent?.waitlist_count" class="text-amber-600">候补 {{ detailEvent?.waitlist_count }} 人</span>
          </div>

          <div v-if="registeredList.length === 0" class="mt-6 text-center py-8 text-sub">
            暂无报名记录
          </div>

          <div v-else class="mt-4 space-y-2">
            <div
              v-for="r in registeredList"
              :key="r.id"
              class="flex items-center gap-3 rounded-xl bg-white/60 px-4 py-3"
            >
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-ink">
                  {{ r.user?.display_name ?? r.user_id.slice(0, 8) }}
                  <span class="text-xs text-faint ml-1">@{{ r.user?.username ?? '' }}</span>
                </p>
                <p class="text-xs text-faint mt-0.5">
                  报名于 {{ fmtDate(r.signup_at) }}
                  <template v-if="r.checkin_at"> · 签到于 {{ fmtDate(r.checkin_at) }}</template>
                </p>
              </div>
              <span
                class="text-xs font-medium rounded-full px-2.5 py-0.5"
                :class="regStatus[r.status]?.cls ?? 'bg-gray-100 text-gray-600'"
              >
                {{ regStatus[r.status]?.text ?? r.status }}
              </span>
              <button
                v-if="r.status === 'registered'"
                class="text-xs px-3 py-1.5 rounded-lg border border-emerald-200 text-emerald-600 hover:bg-emerald-50 transition"
                :disabled="actingId === r.id"
                @click="doCheckin(r)"
              >
                {{ actingId === r.id ? '…' : '签到' }}
              </button>
            </div>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>
