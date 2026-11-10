<script setup lang="ts">
import type { PageRecord, PageVersion } from '@/types'

defineProps<{
  show: boolean
  page: PageRecord | null
  versions: PageVersion[]
  loading: boolean
  actingId: string | null
}>()

const emit = defineEmits<{ close: []; rollback: [v: PageVersion] }>()

function fmtDate(iso: string | null) {
  return iso ? new Date(iso).toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'
}
</script>

<template>
  <Teleport to="body">
    <div v-if="show" class="dialog-overlay" @click.self="emit('close')">
      <div class="glass-card p-6 w-full max-w-lg max-h-[80vh] overflow-auto">
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-bold text-ink">{{ page?.title }} — 版本历史</h2>
          <button class="text-sm text-faint hover:text-ink transition" @click="emit('close')">✕</button>
        </div>

        <div v-if="loading" class="mt-6 text-center py-8">
          <div class="spinner"></div>
          <p class="mt-3 text-sm text-sub">加载中…</p>
        </div>

        <div v-else-if="versions.length === 0" class="mt-6 text-center py-8 text-sub">
          暂无版本记录
        </div>

        <div v-else class="mt-4 space-y-2">
          <div v-for="v in versions" :key="v.id" class="flex items-center gap-3 rounded-xl bg-white/60 px-4 py-3">
            <div class="flex-1">
              <p class="text-sm font-medium text-ink">v{{ v.version }}</p>
              <p class="text-xs text-faint mt-0.5">{{ v.change_summary || '—' }} · {{ fmtDate(v.created_at) }}</p>
            </div>
            <button
              class="btn-sm-primary"
              :disabled="actingId === v.id"
              @click="emit('rollback', v)"
            >
              {{ actingId === v.id ? '…' : '回滚' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
