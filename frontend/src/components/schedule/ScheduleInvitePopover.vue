<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'

type FreeBlock = { weekday: number; lesson_start: number; lesson_end: number }
type CellRect = { top: number; left: number; right: number; bottom: number; width: number; height: number }

const props = defineProps<{
  cell: FreeBlock
  rect: CellRect
  week: number
  partnerName: string
  pinned: boolean
  sending: boolean
  error: string
}>()

const emit = defineEmits<{
  send: [title: string]
  close: []
  hover: [over: boolean]
}>()

const title = ref('一起见面')
const localError = ref('')
const inputRef = ref<HTMLInputElement | null>(null)

watch(
  () => [props.cell.weekday, props.cell.lesson_start, props.cell.lesson_end, props.week] as const,
  () => {
    title.value = '一起见面'
    localError.value = ''
    if (props.pinned) nextTick(() => inputRef.value?.focus())
  },
)

watch(
  () => props.pinned,
  (pinned) => {
    if (pinned) nextTick(() => inputRef.value?.focus())
  },
)

const style = computed(() => {
  const width = 284
  const gap = 12
  const maxLeft = Math.max(12, window.innerWidth - width - 12)
  const left = props.rect.right + gap + width > window.innerWidth
    ? Math.max(12, props.rect.left - width - gap)
    : Math.min(maxLeft, props.rect.right + gap)
  const top = Math.max(12, Math.min(props.rect.top, window.innerHeight - 300))
  return { left: `${left}px`, top: `${top}px`, width: `${width}px` }
})

const timeLabel = computed(() => {
  const day = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][props.cell.weekday] ?? '周一'
  const lessons = props.cell.lesson_start === props.cell.lesson_end
    ? `第 ${props.cell.lesson_start} 节`
    : `第 ${props.cell.lesson_start}-${props.cell.lesson_end} 节`
  return `第 ${props.week} 周 ${day} ${lessons}`
})

function submit() {
  const name = title.value.trim()
  if (!name) {
    localError.value = '请填写邀约名称'
    return
  }
  localError.value = ''
  emit('send', name)
}
</script>

<template>
  <Teleport to="body">
    <form
      class="schedule-invite-popover fixed z-[320] rounded-2xl border border-emerald-200 bg-white/95 p-3.5 text-ink shadow-[0_18px_50px_rgba(31,27,51,0.22)] backdrop-blur-xl"
      :style="style"
      role="dialog"
      aria-label="发起约定"
      @submit.prevent="submit"
      @pointerenter="emit('hover', true)"
      @pointerleave="emit('hover', false)"
    >
      <div class="flex items-start justify-between gap-2">
        <div>
          <p class="text-[10px] font-bold uppercase tracking-[0.16em] text-emerald-600">Invite</p>
          <p class="mt-0.5 text-sm font-bold text-ink">发起约定</p>
        </div>
        <button type="button" class="btn-sm !px-2 !py-0.5 text-xs" aria-label="关闭邀约窗口" :disabled="sending" @click="emit('close')">✕</button>
      </div>

      <label class="label mt-3">邀约名称
        <input ref="inputRef" v-model="title" class="input mt-1" maxlength="128" required :disabled="sending" />
      </label>

      <div class="mt-2 rounded-xl bg-primary-50/70 px-3 py-2 text-xs leading-5 text-sub">
        <p>参与人：<span class="font-semibold text-ink">{{ partnerName || '对方' }}</span></p>
        <p>时间：<span class="font-semibold text-ink">{{ timeLabel }}</span></p>
        <p class="mt-0.5 text-[11px] text-faint">拖动连续空闲格选择多节，单击则选 1 节；对方接受后会自动加入双方「我的日程」。</p>
      </div>

      <p v-if="localError || error" role="alert" class="mt-2 text-xs text-red-600">{{ localError || error }}</p>

      <div class="mt-3 flex items-center justify-end gap-2">
        <button type="button" class="btn-ghost !px-3 !py-1.5 text-xs" :disabled="sending" @click="emit('close')">取消</button>
        <button type="submit" class="btn-primary !px-3 !py-1.5 text-xs" :disabled="sending">
          {{ sending ? '发送中…' : '邀请' }}
        </button>
      </div>
    </form>
  </Teleport>
</template>
