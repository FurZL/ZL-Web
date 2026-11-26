<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { request } from '@/api/client'
import { fetchSiteConfig } from '@/composables/useSiteConfig'
import { useDialog } from '@/composables/useDialog'
import type { ScheduleConfig } from '@/types'

type Overview = { schedules: number; archived: number; public: number; groups: number; appointments_by_status: Record<string, number> }
type AuditItem = { id: string; actor_id: string | null; created_at: string; changes: { before: ScheduleConfig; after: ScheduleConfig } }

const fields: { key: keyof ScheduleConfig; label: string; detail: string }[] = [
  { key: 'file_import_enabled', label: '文件导入', detail: '控制 ICS、TXT 和 PDF 文件导入，不影响浏览器扩展和手工课表。' },
  { key: 'group_join_enabled', label: '创建和加入群组', detail: '关闭后仍可查看和管理已有群组。' },
  { key: 'public_share_enabled', label: '新增公开分享', detail: '关闭后已有公开状态保持不变，用户仍可撤销公开。' },
  { key: 'fixed_invite_enabled', label: '发起固定时间邀约', detail: '关闭后仍可处理已有邀请。' },
]
const statusLabels: Record<string, string> = { pending: '待处理', choosing: '选择中', confirming: '确认中', confirmed: '已确认', declined: '已拒绝', cancelled: '已取消', expired: '已过期' }
const config = ref<ScheduleConfig | null>(null)
const overview = ref<Overview | null>(null)
const audit = ref<AuditItem[]>([])
const error = ref('')
const loading = ref(true)
const saving = ref(false)
const { showToast } = useDialog()

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [settings, stats, records] = await Promise.all([
      request<ScheduleConfig>({ method: 'GET', url: '/admin/schedule/config' }),
      request<Overview>({ method: 'GET', url: '/admin/schedule/overview' }),
      request<{ items: AuditItem[] }>({ method: 'GET', url: '/admin/schedule/audit' }),
    ])
    config.value = settings
    overview.value = stats
    audit.value = records.items
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function save() {
  if (!config.value || saving.value) return
  saving.value = true
  try {
    config.value = await request<ScheduleConfig>({ method: 'PUT', url: '/admin/schedule/config', data: config.value })
    await fetchSiteConfig(true)
    showToast('课表设置已保存')
    try {
      const records = await request<{ items: AuditItem[] }>({ method: 'GET', url: '/admin/schedule/audit' })
      audit.value = records.items
    } catch {
      showToast('设置已保存，但变更记录刷新失败')
    }
  } catch (e) {
    showToast(e instanceof Error ? e.message : '保存失败')
  } finally {
    saving.value = false
  }
}

function describeChanges(item: AuditItem) {
  return fields.filter(field => item.changes.before[field.key] !== item.changes.after[field.key])
    .map(field => `${field.label}：${item.changes.after[field.key] ? '开启' : '关闭'}`).join('、')
}
onMounted(load)
</script>

<template>
  <div>
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-2xl font-bold text-ink">课表运营</h1>
      <button type="button" class="btn-sm" :disabled="loading || saving" @click="load">刷新</button>
    </div>
    <p v-if="error" role="alert" class="mt-4 text-sm text-red-600">{{ error }}</p>
    <p v-if="loading" class="mt-6 text-sm text-sub">正在加载…</p>
    <template v-else-if="config && overview">
      <section class="mt-6">
        <h2 class="text-lg font-semibold text-ink">运行概况</h2>
        <dl class="mt-3 grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-primary-100 bg-primary-100 sm:grid-cols-4">
          <div v-for="item in [{ label: '课表总数', value: overview.schedules }, { label: '已存档', value: overview.archived }, { label: '公开课表', value: overview.public }, { label: '群组总数', value: overview.groups }]" :key="item.label" class="bg-white px-4 py-3">
            <dt class="text-xs text-sub">{{ item.label }}</dt><dd class="mt-1 text-xl font-semibold text-ink">{{ item.value }}</dd>
          </div>
        </dl>
        <p class="mt-3 text-sm text-sub">邀约：<span v-if="!Object.keys(overview.appointments_by_status).length">暂无记录</span><span v-for="(count, status) in overview.appointments_by_status" :key="status" class="mr-3">{{ statusLabels[status] ?? status }} {{ count }}</span></p>
      </section>

      <section class="mt-8 border-t border-primary-100 pt-6">
        <h2 class="text-lg font-semibold text-ink">功能设置</h2>
        <div class="mt-3 divide-y divide-primary-100 border-y border-primary-100">
          <label v-for="field in fields" :key="field.key" class="flex items-center justify-between gap-4 py-4">
            <span><span class="block text-sm font-medium text-ink">{{ field.label }}</span><span class="mt-1 block text-xs text-sub">{{ field.detail }}</span></span>
            <input v-model="config[field.key]" type="checkbox" :disabled="saving" class="h-4 w-4 shrink-0 accent-primary" />
          </label>
        </div>
        <button type="button" class="btn-primary mt-4" :disabled="saving" @click="save">{{ saving ? '保存中…' : '保存设置' }}</button>
      </section>

      <section class="mt-8 border-t border-primary-100 pt-6">
        <h2 class="text-lg font-semibold text-ink">设置变更记录</h2>
        <p v-if="!audit.length" class="mt-3 text-sm text-sub">暂无记录</p>
        <ul v-else class="mt-3 divide-y divide-primary-100 border-y border-primary-100">
          <li v-for="item in audit" :key="item.id" class="py-3 text-sm">
            <p class="text-ink">{{ describeChanges(item) }}</p>
            <p class="mt-1 break-all text-xs text-sub">{{ new Date(item.created_at).toLocaleString() }} · 操作者 {{ item.actor_id ?? '未知' }}</p>
          </li>
        </ul>
      </section>
    </template>
  </div>
</template>
