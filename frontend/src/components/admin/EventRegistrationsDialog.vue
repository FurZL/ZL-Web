<script setup lang="ts">
import { computed } from 'vue'
import type { EventRecord, EventRegistration } from '@/types'

const props = defineProps<{
  show: boolean
  event: EventRecord | null
  registrations: EventRegistration[]
  loading: boolean
  actingId: string | null
}>()

const emit = defineEmits<{ close: []; checkin: [reg: EventRegistration] }>()

const regStatus: Record<string, { text: string; cls: string }> = {
  registered: { text: '已报名', cls: 'bg-emerald-100 text-emerald-700' },
  waitlisted: { text: '候补', cls: 'bg-amber-100 text-amber-700' },
  cancelled: { text: '已取消', cls: 'bg-gray-100 text-gray-500' },
  checked_in: { text: '已签到', cls: 'bg-primary-100 text-primary-700' },
}

function fmtDate(iso: string | null) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const registeredList = computed(() => props.registrations.filter((r) => r.status !== 'cancelled'))
</script>

<template>
  <Teleport to="body">
    <div v-if="show" class="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4" @click.self="emit('close')">
      <div class="glass-card p-6 w-full max-w-xl max-h-[85vh] overflow-auto">
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-bold text-ink">{{ event?.title }} — 报名管理</h2>
          <button class="text-sm text-faint hover:text-ink transition" @click="emit('close')">✕</button>
        </div>

        <div v-if="loading" class="mt-6 text-center py-8">
          <div class="w-8 h-8 border-4 border-primary-200 border-t-primary rounded-full animate-spin mx-auto"></div>
          <p class="mt-3 text-sm text-sub">加载中…</p>
        </div>

        <template v-else>
          <div class="mt-4 flex flex-wrap gap-4 text-sm text-sub">
            <span>👥 正式报名 {{ event?.registered_count }}<template v-if="event?.capacity"> / {{ event?.capacity }}</template> 人</span>
            <span v-if="event?.waitlist_count" class="text-amber-600">候补 {{ event?.waitlist_count }} 人</span>
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
                @click="emit('checkin', r)"
              >
                {{ actingId === r.id ? '…' : '签到' }}
              </button>
            </div>
          </div>
        </template>
      </div>
    </div>
  </Teleport>
</template>
