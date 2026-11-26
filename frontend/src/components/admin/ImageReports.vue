<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { request } from '@/api/client'
import ImageLightbox from '@/components/ImageLightbox.vue'
import { useDialog } from '@/composables/useDialog'
import type { GalleryImage } from '@/types'

type Report = { id: string; image_id: string; image_name: string | null; image_exists: boolean; image_status: string | null; reason: string | null; description: string | null; status: string; created_at: string; handled_at: string | null; handled_by: string | null }
type Result = { items: Report[]; pagination: { page: number; page_size: number; total: number } }
const { showConfirm } = useDialog()
const status = ref('open')
const page = ref(1)
const result = ref<Result>({ items: [], pagination: { page: 1, page_size: 20, total: 0 } })
const error = ref('')
const loading = ref(false)
const acting = ref<string | null>(null)
const preview = ref<GalleryImage | null>(null)
const pages = computed(() => Math.max(1, Math.ceil(result.value.pagination.total / result.value.pagination.page_size)))
const statusLabels: Record<string, string> = { open: '待处理', handled: '已处理', dismissed: '已驳回' }

async function load() {
  loading.value = true
  error.value = ''
  try {
    result.value = await request<Result>({ method: 'GET', url: '/admin/images/reports', params: { status: status.value || undefined, page: page.value, page_size: 20 } })
  } catch (e) { error.value = e instanceof Error ? e.message : '加载举报失败' }
  finally { loading.value = false }
}
async function openImage(report: Report) {
  error.value = ''
  try { preview.value = await request<GalleryImage>({ method: 'GET', url: `/admin/images/reports/${report.id}/image` }) }
  catch (e) { error.value = e instanceof Error ? e.message : '图片加载失败' }
}
async function resolve(report: Report, outcome: 'handled' | 'dismissed' | 'hide') {
  const label = outcome === 'hide' ? '下架图片并处理' : outcome === 'dismissed' ? '驳回举报' : '标记为已处理'
  if (!(await showConfirm(`确定${label}吗？`))) return
  acting.value = report.id
  error.value = ''
  try {
    await request({ method: 'PATCH', url: `/admin/images/reports/${report.id}`, data: { outcome } })
    if (result.value.items.length === 1 && page.value > 1 && status.value) page.value--
    await load()
  } catch (e) { error.value = e instanceof Error ? e.message : '处理举报失败' }
  finally { acting.value = null }
}
onMounted(load)
</script>

<template>
  <section class="mt-6">
    <div class="flex flex-wrap items-end justify-between gap-3">
      <label class="text-sm text-sub">举报状态
        <select v-model="status" class="input mt-1 block min-w-32" @change="page = 1; load()">
          <option value="open">待处理</option><option value="handled">已处理</option><option value="dismissed">已驳回</option><option value="">全部</option>
        </select>
      </label>
      <button class="btn-sm" :disabled="loading" @click="load">刷新</button>
    </div>
    <p v-if="error" role="alert" class="mt-4 text-sm text-red-600">{{ error }}</p>
    <p v-if="loading" class="mt-6 text-sm text-sub">加载中…</p>
    <p v-else-if="!result.items.length" class="mt-6 text-sm text-sub">暂无举报</p>
    <div v-else class="mt-4 divide-y divide-primary-100 border-y border-primary-100">
      <article v-for="report in result.items" :key="report.id" class="py-4">
        <div class="flex flex-wrap items-start justify-between gap-2">
          <div class="min-w-0"><p class="break-all font-medium text-ink">{{ report.image_name || (report.image_exists ? '未命名图片' : '图片已不存在') }}</p><p class="mt-1 break-all text-xs text-sub">图片 ID：{{ report.image_id }}</p></div>
          <span class="text-xs text-sub">{{ statusLabels[report.status] ?? report.status }}</span>
        </div>
        <p class="mt-2 text-sm text-sub">举报原因：{{ report.reason === 'inappropriate' ? '内容不适宜' : report.reason || '未填写' }}</p>
        <p v-if="report.description" class="mt-1 break-words text-sm text-sub">{{ report.description }}</p>
        <p class="mt-1 text-xs text-faint">{{ new Date(report.created_at).toLocaleString() }}<span v-if="report.handled_at"> · 处理于 {{ new Date(report.handled_at).toLocaleString() }}</span></p>
        <div class="mt-3 flex flex-wrap gap-2">
          <button v-if="report.image_exists" class="btn-sm" :disabled="!!acting" @click="openImage(report)">查看图片</button>
          <template v-if="report.status === 'open'"><button class="btn-sm" :disabled="!!acting" @click="resolve(report, 'handled')">标记已处理</button><button class="btn-sm" :disabled="!!acting" @click="resolve(report, 'dismissed')">驳回</button><button v-if="report.image_exists" class="btn-sm text-red-600" :disabled="!!acting" @click="resolve(report, 'hide')">下架并处理</button></template>
        </div>
      </article>
    </div>
    <div class="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm text-sub"><span>共 {{ result.pagination.total }} 条 · 第 {{ page }} / {{ pages }} 页</span><div class="flex gap-2"><button class="btn-sm" :disabled="loading || page <= 1" @click="page--; load()">上一页</button><button class="btn-sm" :disabled="loading || page >= pages" @click="page++; load()">下一页</button></div></div>
    <ImageLightbox :open="!!preview" :title="preview?.description || preview?.title || ''" :image-url="preview ? (preview.display_url || preview.url) : null" :description="preview?.description ?? null" @close="preview = null" />
  </section>
</template>
