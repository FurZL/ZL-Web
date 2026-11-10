<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import {
  adminCreatePage,
  adminDeletePage,
  adminListPages,
  adminListVersions,
  adminPublishPage,
  adminRollbackPage,
  adminUnpublishPage,
  adminUpdatePage,
} from '@/api/pages'
import PageFormDialog from '@/components/admin/PageFormDialog.vue'
import PageVersionsDialog from '@/components/admin/PageVersionsDialog.vue'
import type { PageRecord, PageVersion } from '@/types'
import { useDialog } from '@/composables/useDialog'

const { showConfirm } = useDialog()

const pages = ref<PageRecord[]>([])
const loading = ref(true)
const error = ref('')
const saving = ref(false)

// 创建/编辑弹窗
const showForm = ref(false)
const editingId = ref<string | null>(null)
const form = reactive({
  slug: '',
  title: '',
  seo_title: '',
  seo_description: '',
  schemaText: '',
})

// 版本弹窗
const showVersions = ref(false)
const versionPage = ref<PageRecord | null>(null)
const versions = ref<PageVersion[]>([])
const versionsLoading = ref(false)
const actingId = ref<string | null>(null)

const statusMap: Record<string, { text: string; cls: string }> = {
  draft: { text: '草稿', cls: 'bg-gray-100 text-gray-600' },
  published: { text: '已发布', cls: 'bg-emerald-100 text-emerald-700' },
  archived: { text: '已归档', cls: 'bg-amber-100 text-amber-700' },
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await adminListPages()
    pages.value = data.items
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)

const DEFAULT_SCHEMA = `{
  "title": "活动页面",
  "theme": { "primary": "#6B5CE7", "background": "#F7F6FC" },
  "blocks": [
    { "type": "hero", "props": { "title": "欢迎来到活动现场", "subtitle": "活动介绍" } },
    { "type": "rich_text", "props": { "content": "在这里填写活动介绍内容…" } },
    { "type": "countdown", "props": { "label": "距离活动开始", "target": "2026-12-01T19:00:00+08:00" } },
    { "type": "event_info", "props": { "date": "2026-12-01 19:00", "location": "学生活动中心", "organizer": "福瑞圈" } },
    { "type": "button", "props": { "label": "立即报名", "url": "/events" } }
  ]
}`

function openCreate() {
  editingId.value = null
  Object.assign(form, { slug: '', title: '', seo_title: '', seo_description: '', schemaText: DEFAULT_SCHEMA })
  showForm.value = true
}

function openEdit(p: PageRecord) {
  editingId.value = p.id
  Object.assign(form, {
    slug: p.slug,
    title: p.title,
    seo_title: p.seo_title ?? '',
    seo_description: p.seo_description ?? '',
    schemaText: JSON.stringify(p.schema_json, null, 2),
  })
  showForm.value = true
}

async function save() {
  if (!form.title.trim()) {
    error.value = '标题不能为空'
    return
  }
  let schema: Record<string, unknown>
  try {
    schema = JSON.parse(form.schemaText)
    if (typeof schema !== 'object' || schema === null) {
      error.value = 'Schema 必须是 JSON 对象'
      return
    }
  } catch {
    error.value = 'JSON 格式有误'
    return
  }
  saving.value = true
  error.value = ''
  try {
    if (editingId.value) {
      await adminUpdatePage(editingId.value, {
        title: form.title,
        page_schema: schema,
        seo_title: form.seo_title || null,
        seo_description: form.seo_description || null,
        change_summary: '编辑页面',
      })
    } else {
      await adminCreatePage({
        slug: form.slug,
        title: form.title,
        page_schema: schema,
        seo_title: form.seo_title || null,
        seo_description: form.seo_description || null,
      })
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

async function togglePublish(p: PageRecord) {
  actingId.value = p.id
  try {
    if (p.status === 'published') {
      await adminUnpublishPage(p.id)
    } else {
      await adminPublishPage(p.id)
    }
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '操作失败'
  } finally {
    actingId.value = null
  }
}

async function remove(p: PageRecord) {
  if (!(await showConfirm(`确定删除页面「${p.title}」吗？`))) return
  try {
    await adminDeletePage(p.id)
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '删除失败'
  }
}

async function openVersions(p: PageRecord) {
  versionPage.value = p
  showVersions.value = true
  versionsLoading.value = true
  versions.value = []
  try {
    const data = await adminListVersions(p.id)
    versions.value = data.items
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载版本失败'
  } finally {
    versionsLoading.value = false
  }
}

async function doRollback(v: PageVersion) {
  if (!versionPage.value) return
  if (!(await showConfirm(`确定回滚到版本 v${v.version} 吗？当前内容将被替换。`))) return
  actingId.value = v.id
  try {
    await adminRollbackPage(versionPage.value.id, v.id)
    await openVersions(versionPage.value)
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '回滚失败'
  } finally {
    actingId.value = null
  }
}

function fmtDate(iso: string | null) {
  return iso ? new Date(iso).toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'
}
</script>

<template>
  <div>
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-ink">页面管理</h1>
        <p class="mt-1 text-sm text-sub">动态页面 Schema 编辑、预览、发布与版本回滚</p>
      </div>
      <button class="btn-primary" @click="openCreate">+ 新建页面</button>
    </div>

    <div v-if="error && !showForm && !showVersions" class="mt-4 text-sm text-red-600 bg-red-50 rounded-lg px-4 py-2">{{ error }}</div>

    <div v-if="loading" class="mt-8 glass-card p-12 text-center">
      <div class="w-8 h-8 border-4 border-primary-200 border-t-primary rounded-full animate-spin mx-auto"></div>
      <p class="mt-3 text-sm text-sub">加载中…</p>
    </div>

    <div v-else-if="pages.length === 0" class="mt-8 glass-card p-12 text-center">
      <div class="text-4xl">📄</div>
      <p class="mt-3 text-ink font-medium">还没有动态页面</p>
      <p class="mt-1 text-sm text-sub">点击右上角「新建页面」创建第一条吧</p>
    </div>

    <div v-else class="mt-6 space-y-3">
      <div v-for="p in pages" :key="p.id" class="glass-card p-5 flex flex-col sm:flex-row sm:items-center gap-3">
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <h3 class="font-semibold text-ink truncate">{{ p.title }}</h3>
            <span class="text-xs font-medium rounded-full px-2.5 py-0.5" :class="statusMap[p.status]?.cls ?? 'bg-gray-100 text-gray-600'">
              {{ statusMap[p.status]?.text ?? p.status }}
            </span>
            <code class="text-xs text-faint bg-white/60 rounded px-2 py-0.5">/p/{{ p.slug }}</code>
          </div>
          <div class="mt-1.5 flex flex-wrap items-center gap-3 text-xs text-faint">
            <span v-if="p.published_at">发布于 {{ fmtDate(p.published_at) }}</span>
            <span>更新于 {{ fmtDate(p.updated_at) }}</span>
          </div>
        </div>
        <div class="flex items-center gap-2 shrink-0 flex-wrap">
          <a :href="`/p/${p.slug}`" target="_blank" class="text-xs px-3 py-1.5 rounded-lg border border-primary-200 text-primary-700 hover:bg-primary-50 transition">
            预览
          </a>
          <button class="text-xs px-3 py-1.5 rounded-lg border border-gray-200 text-faint hover:border-primary-200 transition" @click="openEdit(p)">编辑</button>
          <button class="text-xs px-3 py-1.5 rounded-lg border border-gray-200 text-faint hover:border-primary-200 transition" @click="openVersions(p)">版本</button>
          <button
            class="text-xs px-3 py-1.5 rounded-lg border transition"
            :class="p.status === 'published' ? 'border-amber-200 text-amber-600 hover:bg-amber-50' : 'border-emerald-200 text-emerald-600 hover:bg-emerald-50'"
            :disabled="actingId === p.id"
            @click="togglePublish(p)"
          >
            {{ p.status === 'published' ? '下线' : '发布' }}
          </button>
          <button class="text-xs px-3 py-1.5 rounded-lg border border-gray-200 text-red-500 hover:border-red-300 transition" @click="remove(p)">删除</button>
        </div>
      </div>
    </div>

    <!-- 弹窗 -->
    <PageFormDialog
      v-model:form="form"
      :show="showForm"
      :editing="!!editingId"
      :error="error"
      :saving="saving"
      @close="showForm = false; editingId = null"
      @save="save"
    />
    <PageVersionsDialog
      :show="showVersions"
      :page="versionPage"
      :versions="versions"
      :loading="versionsLoading"
      :acting-id="actingId"
      @close="showVersions = false; versionPage = null; versions = []"
      @rollback="doRollback"
    />
  </div>
</template>
