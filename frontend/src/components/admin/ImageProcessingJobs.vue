<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { request } from '@/api/client'
import { useDialog } from '@/composables/useDialog'

type Job = { id: string; image_id: string; kind: string; status: string; attempts: number; next_attempt_at: string; created_at: string; updated_at: string }
type Page = { items: Job[]; pagination: { page: number; page_size: number; total: number } }
const { showConfirm } = useDialog()
const page = ref(1)
const filter = ref('failed')
const result = ref<Page>({ items: [], pagination: { page: 1, page_size: 20, total: 0 } })
const loading = ref(false)
const acting = ref<string | null>(null)
const error = ref('')
const pages = computed(() => Math.max(1, Math.ceil(result.value.pagination.total / result.value.pagination.page_size)))
const labels: Record<string, string> = { pending: '等待处理', processing: '处理中', failed: '处理失败', done: '已完成' }

async function load() {
  loading.value = true; error.value = ''
  try { result.value = await request<Page>({ method: 'GET', url: '/admin/images/processing-jobs', params: { status: filter.value || undefined, page: page.value, page_size: 20 } }) }
  catch (e) { error.value = e instanceof Error ? e.message : '加载任务失败' }
  finally { loading.value = false }
}
async function retry(job: Job) {
  if (!(await showConfirm('确定重新处理这张图片吗？'))) return
  acting.value = job.id; error.value = ''
  try {
    await request({ method: 'POST', url: `/admin/images/processing-jobs/${job.id}/retry` })
    if (result.value.items.length === 1 && page.value > 1 && filter.value) page.value--
    await load()
  } catch (e) { error.value = e instanceof Error ? e.message : '重试失败' }
  finally { acting.value = null }
}
onMounted(load)
</script>

<template>
  <section class="mt-6">
    <div class="flex flex-wrap items-end justify-between gap-3">
      <label class="text-sm text-sub">任务状态<select v-model="filter" class="input mt-1 block min-w-32" @change="page = 1; load()"><option value="failed">处理失败</option><option value="pending">等待处理</option><option value="processing">处理中</option><option value="done">已完成</option><option value="">全部</option></select></label>
      <button class="btn-sm" :disabled="loading" @click="load">刷新</button>
    </div>
    <p v-if="error" role="alert" class="mt-4 text-sm text-red-600">{{ error }}</p>
    <p v-if="loading" class="mt-6 text-sm text-sub">加载中…</p>
    <p v-else-if="!result.items.length" class="mt-6 text-sm text-sub">暂无任务</p>
    <div v-else class="mt-4 divide-y divide-primary-100 border-y border-primary-100">
      <article v-for="job in result.items" :key="job.id" class="flex flex-wrap items-center justify-between gap-3 py-4 text-sm">
        <div class="min-w-0"><p class="font-medium text-ink">{{ job.kind === 'profile' ? '个人相册' : '公开图库' }} · {{ labels[job.status] ?? job.status }}</p><p class="mt-1 break-all text-xs text-sub">图片 ID：{{ job.image_id }} · 尝试 {{ job.attempts }} 次</p><p class="mt-1 text-xs text-faint">更新于 {{ new Date(job.updated_at).toLocaleString() }}</p></div>
        <button v-if="job.status === 'failed'" class="btn-sm" :disabled="!!acting" @click="retry(job)">重新处理</button>
      </article>
    </div>
    <div class="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm text-sub"><span>共 {{ result.pagination.total }} 条 · 第 {{ page }} / {{ pages }} 页</span><div class="flex gap-2"><button class="btn-sm" :disabled="loading || page <= 1" @click="page--; load()">上一页</button><button class="btn-sm" :disabled="loading || page >= pages" @click="page++; load()">下一页</button></div></div>
  </section>
</template>
