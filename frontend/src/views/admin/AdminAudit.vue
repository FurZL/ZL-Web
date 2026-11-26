<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { request } from '@/api/client'

type AuditItem = { id: string; actor_id: string | null; actor_name: string | null; action: string; target_type: string | null; target_id: string | null; request_id: string | null; ip_masked: string | null; changes: Record<string, unknown>; created_at: string }
type AuditPage = { items: AuditItem[]; total: number; page: number; page_size: number }

const categories: Record<string, string> = { user: '用户', site_setting: '网站设置', image: '图片', image_job: '图片任务', report: '举报', announcement: '公告', event: '活动', event_registration: '活动签到', page: '页面' }
const actions: Record<string, string> = { approve_user: '审批通过', reject_user: '审批拒绝', set_role: '修改角色', set_status: '修改状态', upsert_setting: '修改设置', update_intro: '修改社团介绍', set_image_moderation: '图片审核', set_image_visibility: '修改可见性', set_image_tags: '修改标签', remove_image: '删除图片', create_announcement: '创建公告', update_announcement: '修改公告', delete_announcement: '删除公告', create_event: '创建活动', update_event: '修改活动', set_event_status: '修改活动状态', delete_event: '删除活动', admin_checkin: '活动签到', create_page: '创建页面', update_page: '修改页面', publish_page: '发布页面', unpublish_page: '下线页面', delete_page: '删除页面', rollback_page: '回滚页面', 'schedule.config.update': '修改课表设置' }
actions.resolve_report = '处理图片举报'
actions.retry_processing_job = '重试图片任务'
const fields: Record<string, string> = { role: '角色', status: '状态', is_active: '启用', category: '分类', is_public: '公开', value_json: '设置内容', moderation_status: '审核状态', tags: '标签', title: '标题', content: '正文', is_pinned: '置顶', published_at: '发布时间', expires_at: '过期时间', starts_at: '开始时间', ends_at: '结束时间', capacity: '人数上限', description: '描述', location: '地点', schema_json: '页面内容', checkin_at: '签到时间', registration_enabled: '允许注册', require_email_verification: '邮箱验证', require_phone_verification: '手机验证', enabled: '启用', qq_enabled: 'QQ 登录' }
const targetType = ref('')
const action = ref('')
const actorId = ref('')
const start = ref('')
const end = ref('')
const records = ref<AuditPage>({ items: [], total: 0, page: 1, page_size: 20 })
const loading = ref(false)
const error = ref('')
const pages = computed(() => Math.max(1, Math.ceil(records.value.total / records.value.page_size)))

async function load(page = 1) {
  loading.value = true
  error.value = ''
  try {
    records.value = await request<AuditPage>({ method: 'GET', url: '/admin/audit', params: {
      page, page_size: 20, target_type: targetType.value || undefined,
      action: action.value.trim() || undefined, actor_id: actorId.value.trim() || undefined,
      start: start.value ? new Date(start.value).toISOString() : undefined,
      end: end.value ? new Date(end.value).toISOString() : undefined,
    } })
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

function actionLabel(value: string) {
  const parts = value.split('.')
  return actions[value] ?? actions[parts[parts.length - 1] ?? ''] ?? value
}

function fieldLabel(value: string) { return fields[value] ?? value }
function formatValue(value: unknown) {
  if (value === true) return '是'
  if (value === false) return '否'
  if (value === null || value === undefined) return '无'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}
onMounted(() => load())
</script>

<template>
  <div>
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-2xl font-bold text-ink">操作审计</h1>
      <RouterLink to="/admin/settings" class="btn-sm">返回网站设置</RouterLink>
    </div>
    <form class="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3" @submit.prevent="load(1)">
      <label class="text-sm text-sub">对象类型
        <select v-model="targetType" class="input mt-1 w-full"><option value="">全部</option><option v-for="(label, key) in categories" :key="key" :value="key">{{ label }}</option></select>
      </label>
      <label class="text-sm text-sub">操作代码<input v-model="action" class="input mt-1 w-full" placeholder="例如 user.set_role" /></label>
      <label class="text-sm text-sub">操作者 ID<input v-model="actorId" class="input mt-1 w-full" placeholder="用户 UUID" /></label>
      <label class="text-sm text-sub">开始时间<input v-model="start" type="datetime-local" class="input mt-1 w-full" /></label>
      <label class="text-sm text-sub">结束时间<input v-model="end" type="datetime-local" class="input mt-1 w-full" /></label>
      <div class="flex items-end"><button type="submit" class="btn-primary" :disabled="loading">查询</button></div>
    </form>
    <p v-if="error" role="alert" class="mt-4 text-sm text-red-600">{{ error }}</p>
    <p v-if="loading" class="mt-6 text-sm text-sub">正在加载…</p>
    <p v-else-if="!records.items.length" class="mt-6 text-sm text-sub">没有符合条件的记录</p>
    <div v-else class="mt-6 divide-y divide-primary-100 border-y border-primary-100">
      <article v-for="item in records.items" :key="item.id" class="py-4 text-sm">
        <div class="flex flex-wrap items-baseline justify-between gap-2"><strong class="text-ink">{{ actionLabel(item.action) }}</strong><time class="text-xs text-sub">{{ new Date(item.created_at).toLocaleString() }}</time></div>
        <p class="mt-1 break-all text-xs text-sub">{{ categories[item.target_type ?? ''] ?? item.target_type ?? '未知对象' }} · {{ item.target_id ?? '未知' }} · 操作者 {{ item.actor_name ?? item.actor_id ?? '未知' }}</p>
        <p class="mt-1 break-all text-xs text-sub">{{ item.action }}<span v-if="item.request_id"> · 请求 {{ item.request_id }}</span><span v-if="item.ip_masked"> · IP {{ item.ip_masked }}</span></p>
        <details class="mt-2 text-xs text-sub"><summary class="cursor-pointer">查看变更</summary>
          <div class="mt-2 space-y-1 break-all">
            <p v-if="Array.isArray(item.changes.fields_changed)">涉及字段：{{ item.changes.fields_changed.map((v: string) => fieldLabel(v)).join('、') }}</p>
            <p v-for="(value, key) in (item.changes.after as Record<string, unknown> ?? {})" :key="key">{{ fieldLabel(String(key)) }}：{{ formatValue((item.changes.before as Record<string, unknown> ?? {})[key]) }} → {{ formatValue(value) }}</p>
            <p v-if="!item.changes.fields_changed && !item.changes.after">无变更详情</p>
          </div>
        </details>
      </article>
    </div>
    <div class="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm text-sub">
      <span>共 {{ records.total }} 条 · 第 {{ records.page }} / {{ pages }} 页</span>
      <div class="flex gap-2"><button class="btn-sm" :disabled="loading || records.page <= 1" @click="load(records.page - 1)">上一页</button><button class="btn-sm" :disabled="loading || records.page >= pages" @click="load(records.page + 1)">下一页</button></div>
    </div>
  </div>
</template>
