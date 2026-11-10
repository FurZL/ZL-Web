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
import EventFormDialog from '@/components/admin/EventFormDialog.vue'
import EventRegistrationsDialog from '@/components/admin/EventRegistrationsDialog.vue'
import type { EventRecord, EventRegistration } from '@/types'
import { useDialog } from '@/composables/useDialog'

const { showConfirm } = useDialog()

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

// 报名管理弹窗
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
  Object.assign(form, {
    title: '', description: '', location: '', starts_at: '', ends_at: '',
    capacity: '', registration_starts_at: '', registration_ends_at: '', publish_now: true,
  })
  showForm.value = true
}

function openEdit(e: EventRecord) {
  editingId.value = e.id
  Object.assign(form, {
    title: e.title,
    description: e.description ?? '',
    location: e.location ?? '',
    starts_at: e.starts_at ? e.starts_at.slice(0, 16) : '',
    ends_at: e.ends_at ? e.ends_at.slice(0, 16) : '',
    capacity: e.capacity ?? '',
    registration_starts_at: e.registration_starts_at ? e.registration_starts_at.slice(0, 16) : '',
    registration_ends_at: e.registration_ends_at ? e.registration_ends_at.slice(0, 16) : '',
    publish_now: e.status === 'published',
  })
  showForm.value = true
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
      registration_starts_at: form.registration_starts_at ? new Date(form.registration_starts_at).toISOString() : null,
      registration_ends_at: form.registration_ends_at ? new Date(form.registration_ends_at).toISOString() : null,
    }
    if (editingId.value) {
      await adminUpdateEvent(editingId.value, payload)
    } else {
      await adminCreateEvent({ ...payload, publish_now: form.publish_now })
    }
    showForm.value = false
    editingId.value = null
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '保存失败'
  } finally {
    saving.value = false
  }
}

async function toggleStatus(e: EventRecord) {
  try {
    await adminSetEventStatus(e.id, e.status === 'published' ? 'draft' : 'published')
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '操作失败'
  }
}

async function cancelEvent(e: EventRecord) {
  if (!(await showConfirm(`确定取消活动「${e.title}」吗？`))) return
  try {
    await adminSetEventStatus(e.id, 'cancelled')
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '操作失败'
  }
}

async function removeEvent(e: EventRecord) {
  if (!(await showConfirm(`确定删除活动「${e.title}」吗？此操作不可恢复。`))) return
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

function fmtDate(iso: string | null) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

const eventStatus: Record<string, { text: string; cls: string }> = {
  draft: { text: '草稿', cls: 'bg-gray-100 text-gray-600' },
  published: { text: '已发布', cls: 'bg-emerald-100 text-emerald-700' },
  cancelled: { text: '已取消', cls: 'bg-red-100 text-red-600' },
}

const sortedEvents = computed(() =>
  [...events.value].sort((a, b) => (b.starts_at ?? '').localeCompare(a.starts_at ?? '')),
)
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
      <div v-for="e in sortedEvents" :key="e.id" class="glass-card p-5 flex flex-col sm:flex-row sm:items-center gap-3">
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <h3 class="font-semibold text-ink truncate">{{ e.title }}</h3>
            <span class="text-xs font-medium rounded-full px-2.5 py-0.5" :class="eventStatus[e.status]?.cls ?? 'bg-gray-100 text-gray-600'">
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
          <button class="text-xs px-3 py-1.5 rounded-lg border border-primary-200 text-primary-700 hover:bg-primary-50 transition" @click="openDetail(e)">报名/签到</button>
          <button class="text-xs px-3 py-1.5 rounded-lg border border-gray-200 text-faint hover:border-primary-200 transition" @click="openEdit(e)">编辑</button>
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
          <button class="text-xs px-3 py-1.5 rounded-lg border border-gray-200 text-red-500 hover:border-red-300 transition" @click="removeEvent(e)">删除</button>
        </div>
      </div>
    </div>

    <!-- 弹窗 -->
    <EventFormDialog
      v-model:form="form"
      :show="showForm"
      :editing="!!editingId"
      :error="error"
      :saving="saving"
      @close="showForm = false; editingId = null"
      @save="save"
    />
    <EventRegistrationsDialog
      :show="showDetail"
      :event="detailEvent"
      :registrations="detailRegs"
      :loading="detailLoading"
      :acting-id="actingId"
      @close="showDetail = false; detailEvent = null; detailRegs = []"
      @checkin="doCheckin"
    />
  </div>
</template>
