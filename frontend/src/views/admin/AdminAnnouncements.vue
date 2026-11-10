<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  createAnnouncement,
  deleteAnnouncement,
  getAllAnnouncements,
  updateAnnouncement,
} from '@/api/site'
import type { AnnouncementRecord } from '@/types'
import { useDialog } from '@/composables/useDialog'

const { showConfirm } = useDialog()

const announcements = ref<AnnouncementRecord[]>([])
const loading = ref(true)
const error = ref('')
const saving = ref(false)

// 新建/编辑弹窗
const showForm = ref(false)
const editingId = ref<string | null>(null)
const form = ref({
  title: '',
  content: '',
  is_pinned: false,
  publish_now: true,
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await getAllAnnouncements()
    announcements.value = data.items
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)

function openCreate() {
  editingId.value = null
  form.value = { title: '', content: '', is_pinned: false, publish_now: true }
  showForm.value = true
}

function openEdit(a: AnnouncementRecord) {
  editingId.value = a.id
  form.value = {
    title: a.title,
    content: a.content,
    is_pinned: a.is_pinned,
    publish_now: a.status === 'published',
  }
  showForm.value = true
}

function closeForm() {
  showForm.value = false
  editingId.value = null
}

async function save() {
  if (!form.value.title.trim() || !form.value.content.trim()) {
    error.value = '标题和内容不能为空'
    return
  }
  saving.value = true
  error.value = ''
  try {
    if (editingId.value) {
      await updateAnnouncement(editingId.value, {
        title: form.value.title,
        content: form.value.content,
        is_pinned: form.value.is_pinned,
        publish_now: form.value.publish_now,
      })
    } else {
      await createAnnouncement({
        title: form.value.title,
        content: form.value.content,
        is_pinned: form.value.is_pinned,
        publish_now: form.value.publish_now,
      })
    }
    closeForm()
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '保存失败'
  } finally {
    saving.value = false
  }
}

async function togglePin(a: AnnouncementRecord) {
  try {
    await updateAnnouncement(a.id, { is_pinned: !a.is_pinned })
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '操作失败'
  }
}

async function togglePublish(a: AnnouncementRecord) {
  try {
    await updateAnnouncement(a.id, { publish_now: a.status !== 'published' })
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '操作失败'
  }
}

async function remove(a: AnnouncementRecord) {
  if (!(await showConfirm(`确定删除公告「${a.title}」吗？`))) return
  try {
    await deleteAnnouncement(a.id)
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '删除失败'
  }
}

const statusLabel: Record<string, { text: string; cls: string }> = {
  draft: { text: '草稿', cls: 'bg-gray-100 text-gray-600' },
  published: { text: '已发布', cls: 'bg-emerald-100 text-emerald-700' },
  expired: { text: '已过期', cls: 'bg-amber-100 text-amber-700' },
}

function fmtDate(iso: string | null) {
  return iso ? iso.slice(0, 10) : '—'
}

const sortedAnnouncements = computed(() =>
  [...announcements.value].sort((a, b) => {
    if (a.is_pinned !== b.is_pinned) return a.is_pinned ? -1 : 1
    return (b.published_at ?? b.created_at ?? '').localeCompare(a.published_at ?? a.created_at ?? '')
  }),
)
</script>

<template>
  <div>
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-ink">公告管理</h1>
        <p class="mt-1 text-sm text-sub">创建、编辑、发布社团公告</p>
      </div>
      <button class="btn-primary" @click="openCreate">+ 新建公告</button>
    </div>

    <div v-if="error && !showForm" class="mt-4 text-sm text-red-600 bg-red-50 rounded-lg px-4 py-2">{{ error }}</div>

    <!-- 公告列表 -->
    <div v-if="loading" class="mt-8 glass-card p-12 text-center">
      <div class="w-8 h-8 border-4 border-primary-200 border-t-primary rounded-full animate-spin mx-auto"></div>
      <p class="mt-3 text-sm text-sub">加载中…</p>
    </div>

    <div v-else-if="sortedAnnouncements.length === 0" class="mt-8 glass-card p-12 text-center">
      <div class="text-4xl">📢</div>
      <p class="mt-3 text-ink font-medium">还没有公告</p>
      <p class="mt-1 text-sm text-sub">点击右上角「新建公告」创建第一条吧</p>
    </div>

    <div v-else class="mt-6 space-y-3">
      <div
        v-for="a in sortedAnnouncements"
        :key="a.id"
        class="glass-card p-5 flex flex-col sm:flex-row sm:items-center gap-3"
      >
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <span
              v-if="a.is_pinned"
              class="text-xs font-medium text-primary-700 bg-primary-100 rounded-full px-2.5 py-0.5"
            >
              置顶
            </span>
            <span
              class="text-xs font-medium rounded-full px-2.5 py-0.5"
              :class="statusLabel[a.status]?.cls ?? 'bg-gray-100 text-gray-600'"
            >
              {{ statusLabel[a.status]?.text ?? a.status }}
            </span>
            <span class="text-xs text-faint">{{ fmtDate(a.published_at || a.created_at) }}</span>
          </div>
          <h3 class="mt-1.5 font-semibold text-ink truncate">{{ a.title }}</h3>
          <p class="mt-1 text-sm text-sub line-clamp-2">{{ a.content }}</p>
        </div>
        <div class="flex items-center gap-2 shrink-0">
          <button
            class="text-xs px-3 py-1.5 rounded-lg border transition"
            :class="a.is_pinned ? 'border-primary-300 text-primary-700 bg-primary-50' : 'border-gray-200 text-faint hover:border-primary-200'"
            @click="togglePin(a)"
          >
            {{ a.is_pinned ? '取消置顶' : '置顶' }}
          </button>
          <button
            class="text-xs px-3 py-1.5 rounded-lg border transition"
            :class="a.status === 'published' ? 'border-emerald-300 text-emerald-700 bg-emerald-50' : 'border-gray-200 text-faint hover:border-emerald-200'"
            @click="togglePublish(a)"
          >
            {{ a.status === 'published' ? '撤回' : '发布' }}
          </button>
          <button class="text-xs px-3 py-1.5 rounded-lg border border-gray-200 text-faint hover:border-primary-200 transition" @click="openEdit(a)">
            编辑
          </button>
          <button class="text-xs px-3 py-1.5 rounded-lg border border-gray-200 text-red-500 hover:border-red-300 transition" @click="remove(a)">
            删除
          </button>
        </div>
      </div>
    </div>

    <!-- 新建/编辑弹窗 -->
    <div v-if="showForm" class="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4" @click.self="closeForm">
      <div class="glass-card p-6 w-full max-w-lg max-h-[80vh] overflow-auto">
        <h2 class="text-lg font-bold text-ink">{{ editingId ? '编辑公告' : '新建公告' }}</h2>
        <div v-if="error && showForm" class="mt-3 text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{{ error }}</div>
        <div class="mt-4 space-y-4">
          <div>
            <label class="label">标题</label>
            <input v-model="form.title" class="input" placeholder="公告标题" maxlength="255" />
          </div>
          <div>
            <label class="label">内容</label>
            <textarea v-model="form.content" class="input min-h-[120px]" rows="5" placeholder="公告正文内容…"></textarea>
          </div>
          <div class="flex items-center gap-4">
            <label class="flex items-center gap-2 text-sm text-sub cursor-pointer">
              <input v-model="form.is_pinned" type="checkbox" class="accent-primary" />
              置顶
            </label>
            <label class="flex items-center gap-2 text-sm text-sub cursor-pointer">
              <input v-model="form.publish_now" type="checkbox" class="accent-primary" />
              立即发布
            </label>
          </div>
        </div>
        <div class="mt-6 flex gap-3">
          <button class="btn-ghost flex-1" @click="closeForm">取消</button>
          <button class="btn-primary flex-1" :disabled="saving" @click="save">
            {{ saving ? '保存中…' : '保存' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
