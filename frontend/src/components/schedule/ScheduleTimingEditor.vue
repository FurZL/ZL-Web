<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, toRaw } from 'vue'
import type { ScheduleTiming } from '@/types'
import { MIN_LESSON, nextSchedulePeriod, normalizeScheduleTiming, periodSegment, periodSegmentLabel } from './calendar'

const props = withDefaults(defineProps<{
  initial?: ScheduleTiming | null
  saving: boolean
  error: string
  usedLesson?: number
}>(), { usedLesson: 0 })
const emit = defineEmits<{ close: []; save: [timing: ScheduleTiming] }>()
const timing = reactive<ScheduleTiming>(structuredClone(normalizeScheduleTiming(toRaw(props.initial))))
const validation = ref('')
let returnFocus: HTMLElement | null = null
const endOfDay = computed(() => timing.periods[timing.periods.length - 1]?.[1] ?? '')

function minutes(value: string) {
  const [h, m] = value.split(':').map(Number)
  return h * 60 + m
}
function clock(value: number) {
  return `${String(Math.floor(value / 60)).padStart(2, '0')}:${String(value % 60).padStart(2, '0')}`
}
function regenerate() {
  const start = minutes(timing.first_start)
  timing.periods = Array.from({ length: timing.periods.length }, (_, index) => {
    const lessonStart = start + index * (timing.lesson_minutes + timing.break_minutes)
    return [clock(lessonStart), clock(lessonStart + timing.lesson_minutes)]
  })
  validation.value = ''
}
function addPeriod() {
  const next = nextSchedulePeriod(timing)
  if (!next) return
  timing.periods.push(next)
  validation.value = ''
}
function canAddPeriod() {
  return nextSchedulePeriod(timing) !== null
}
function canRemovePeriod() {
  return timing.periods.length > Math.max(MIN_LESSON, props.usedLesson)
}
function removeLastPeriod() {
  if (!canRemovePeriod()) return
  timing.periods.pop()
  validation.value = ''
}
function useFirstPeriod() {
  timing.first_start = timing.periods[0][0]
}
function segmentLabelAt(index: number) {
  const current = periodSegment(timing, index)
  const previous = index > 0 ? periodSegment(timing, index - 1) : null
  return index === 0 || current !== previous ? periodSegmentLabel(current) : ''
}
function segmentClassAt(index: number) {
  return `timing-period-label--${periodSegment(timing, index)}`
}
function submit() {
  validation.value = ''
  if (timing.term_start && new Date(`${timing.term_start}T12:00:00Z`).getUTCDay() !== 1) {
    validation.value = '学期第一周开始日期必须是周一'
    return
  }
  const noon = minutes(timing.segments.noon)
  const afternoon = minutes(timing.segments.afternoon)
  const evening = minutes(timing.segments.evening)
  if (!(noon < afternoon && afternoon < evening)) {
    validation.value = '时段边界必须按 中午 < 下午 < 晚上 的顺序排列'
    return
  }
  if (timing.periods.some(([start, end], i) => end <= start || (i > 0 && timing.periods[i - 1][1] > start))) {
    validation.value = '每节课的结束时间须晚于开始时间，节次之间不能重叠'
    return
  }
  useFirstPeriod()
  const rawTiming = toRaw(timing)
  emit('save', structuredClone({ ...rawTiming, first_start: rawTiming.periods[0][0] }))
}
onMounted(() => {
  returnFocus = document.activeElement as HTMLElement | null
})
onBeforeUnmount(() => {
  returnFocus?.focus()
})
</script>

<template>
  <Teleport to="body">
    <div class="dialog-overlay timing-dialog-overlay" role="dialog" aria-modal="true" aria-labelledby="timing-title"
      @click.self="!saving && emit('close')" @keydown.esc.stop="!saving && emit('close')">
      <form class="space-y-5 p-5 sm:p-7" @submit.prevent="submit">
        <div class="flex items-start justify-between gap-3">
          <div>
            <h2 id="timing-title" class="text-xl font-bold">课表作息设置</h2>
            <p class="mt-1 text-sm text-sub">节次时间会显示在课表上，也会用于约饭空闲计算。</p>
          </div>
          <button type="button" class="btn-sm" aria-label="关闭作息设置" :disabled="saving" @click="emit('close')">✕</button>
        </div>

        <section class="grid gap-3 sm:grid-cols-3">
          <label class="label">学期第一周周一
            <input v-model="timing.term_start" type="date" class="input mt-1" />
          </label>
          <label class="label">第一节开始时间
            <input v-model="timing.first_start" type="time" required class="input mt-1" />
          </label>
          <label class="label">每节课时长（分钟）
            <input v-model.number="timing.lesson_minutes" type="number" min="15" max="180" required class="input mt-1" />
          </label>
          <label class="label sm:col-span-2">默认节间隔（分钟）
            <input v-model.number="timing.break_minutes" type="number" min="0" max="180" required class="input mt-1" />
          </label>
          <button type="button" class="btn-ghost self-end" :disabled="saving" @click="regenerate">按当前节数重排</button>
        </section>

        <section class="rounded-xl border border-primary-100 bg-primary-50/45 p-3">
          <p class="text-xs font-semibold text-sub">时段划分（按每节开始时间自动归类）</p>
          <div class="mt-2 grid gap-3 sm:grid-cols-3">
            <label class="label">上午结束 / 中午开始
              <input v-model="timing.segments.noon" type="time" required class="input mt-1" />
            </label>
            <label class="label">中午结束 / 下午开始
              <input v-model="timing.segments.afternoon" type="time" required class="input mt-1" />
            </label>
            <label class="label">下午结束 / 晚上开始
              <input v-model="timing.segments.evening" type="time" required class="input mt-1" />
            </label>
          </div>
          <p class="mt-2 text-xs leading-5 text-sub">上午从当天第一节课开始；默认 12:00 / 14:00 / 18:00，可自由调整，网格上的分段会随之变化。</p>
        </section>

        <section class="overflow-hidden rounded-xl border border-primary-100">
          <div class="flex items-center justify-between gap-3 bg-primary-50 px-3 py-2">
            <p class="text-xs font-semibold text-sub">节次时间（{{ timing.periods.length }} 节）</p>
            <div class="flex gap-2">
              <button type="button" class="btn-xs-success" :disabled="saving || !canAddPeriod()" title="当天时间不足以容纳下一节时，请先调整开始时间、课时或节间隔" @click="addPeriod">＋ 添加一节</button>
              <button type="button" class="btn-xs-danger" :disabled="saving || !canRemovePeriod()" title="删除最后一节" @click="removeLastPeriod">− 删除</button>
            </div>
          </div>
          <div class="grid grid-cols-[6rem_minmax(0,1fr)_minmax(0,1fr)] gap-2 border-t border-primary-100 bg-primary-50/60 px-3 py-2 text-xs font-semibold text-sub">
            <span>节次</span><span>开始</span><span>结束</span>
          </div>
          <div class="grid max-h-[38dvh] grid-cols-[6rem_minmax(0,1fr)_minmax(0,1fr)] gap-x-2 gap-y-1 overflow-y-auto p-3">
            <template v-for="(_, index) in timing.periods" :key="index">
              <label class="timing-period-label flex items-center text-sm font-semibold">
                <span v-if="segmentLabelAt(index)" class="timing-segment" :class="segmentClassAt(index)">{{ segmentLabelAt(index) }}</span>
                第 {{ index + 1 }} 节
              </label>
              <input v-model="timing.periods[index][0]" type="time" class="input !px-2" :aria-label="`第 ${index + 1} 节开始时间`" @change="index === 0 && useFirstPeriod()" />
              <input v-model="timing.periods[index][1]" type="time" class="input !px-2" :aria-label="`第 ${index + 1} 节结束时间`" />
            </template>
          </div>
        </section>
        <p class="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800">预览：第 1 节 {{ timing.periods[0][0] }}–{{ timing.periods[0][1] }} · 第 {{ timing.periods.length }} 节 {{ endOfDay }}</p>
        <p v-if="validation || error" role="alert" class="text-sm text-red-700">{{ validation || error }}</p>
        <footer class="flex justify-end gap-2">
          <button type="button" class="btn-ghost" :disabled="saving" @click="emit('close')">取消</button>
          <button type="submit" class="btn-primary" :disabled="saving">{{ saving ? '保存中…' : '保存作息' }}</button>
        </footer>
      </form>
    </div>
  </Teleport>
</template>

<style scoped>
.timing-dialog-overlay { background: rgb(31 27 51 / 45%); backdrop-filter: blur(4px); }
.timing-dialog-overlay > form { width: min(42rem, calc(100vw - 1.5rem)); max-height: calc(100dvh - 1.5rem); overflow-y: auto; border-radius: 1rem; background: white; color: theme('colors.ink'); box-shadow: theme('boxShadow.glass'); }
.timing-period-label { gap: 0.35rem; white-space: nowrap; }
.timing-segment { border-radius: 999px; padding: 0.15rem 0.35rem; font-size: 0.58rem; line-height: 1; }
.timing-period-label--morning .timing-segment { background: #eef2ff; color: #4f46e5; }
.timing-period-label--noon .timing-segment { background: #fff7ed; color: #c2410c; }
.timing-period-label--afternoon .timing-segment { background: #ecfdf5; color: #047857; }
.timing-period-label--evening .timing-segment { background: #f3e8ff; color: #7e22ce; }
</style>
