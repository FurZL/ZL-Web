<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import type { ScheduleSlot, ScheduleTiming } from '@/types'
import { DEFAULT_LESSON_COUNT, MAX_LESSON, defaultScheduleSegments } from './calendar'

const props = withDefaults(defineProps<{
  importId: string
  initialName: string
  slots: ScheduleSlot[]
  saving: boolean
  error: string
  title?: string
  notices?: string[]
}>(), {
  title: '确认导入教务课表',
  notices: () => [],
})

const emit = defineEmits<{
  close: []
  save: [value: { importId: string; name: string; slots: ScheduleSlot[]; timing: ScheduleTiming }]
}>()

const form = reactive({
  name: props.initialName || '浙江理工课表',
  term_start: '',
  first_start: '08:00',
  lesson_minutes: 45,
  break_minutes: 10,
})
const validation = ref('')

const lessonCount = computed(() => Math.min(MAX_LESSON, Math.max(
  DEFAULT_LESSON_COUNT,
  ...props.slots.map((slot) => slot.lesson_end),
)))

function minutes(value: string) {
  const [hour, minute] = value.split(':').map(Number)
  return hour * 60 + minute
}

function clock(value: number) {
  return `${String(Math.floor(value / 60)).padStart(2, '0')}:${String(value % 60).padStart(2, '0')}`
}

const timing = computed<ScheduleTiming | null>(() => {
  const start = minutes(form.first_start)
  const lesson = Number(form.lesson_minutes)
  const gap = Number(form.break_minutes)
  if (!Number.isFinite(start) || !Number.isFinite(lesson) || !Number.isFinite(gap)) return null
  const periods: [string, string][] = []
  for (let index = 0; index < lessonCount.value; index += 1) {
    const begins = start + index * (lesson + gap)
    const ends = begins + lesson
    if (ends >= 24 * 60) return null
    periods.push([clock(begins), clock(ends)])
  }
  return {
    term_start: form.term_start || null,
    first_start: form.first_start,
    lesson_minutes: lesson,
    break_minutes: gap,
    segments: defaultScheduleSegments(),
    periods,
  }
})

function dayName(day: number) {
  return ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][day] ?? '未知星期'
}

function submit() {
  validation.value = ''
  const selectedTiming = timing.value
  if (!form.name.trim()) {
    validation.value = '请填写课表名称'
    return
  }
  if (form.term_start && new Date(`${form.term_start}T12:00:00Z`).getUTCDay() !== 1) {
    validation.value = '学期第一周开始日期必须是周一'
    return
  }
  if (!selectedTiming) {
    validation.value = '当前节数超出当天作息时间，请调整开始时间、课时或节间隔'
    return
  }
  emit('save', {
    importId: props.importId,
    name: form.name.trim(),
    slots: props.slots,
    timing: selectedTiming,
  })
}
</script>

<template>
  <Teleport to="body">
    <div class="dialog-overlay schedule-import-overlay" role="dialog" aria-modal="true" aria-labelledby="schedule-import-title"
      @click.self="!saving && emit('close')" @keydown.esc.stop="!saving && emit('close')">
      <form class="schedule-import-dialog" @submit.prevent="submit">
        <header class="flex items-start justify-between gap-3">
          <div>
            <h2 id="schedule-import-title" class="text-lg font-bold text-ink">{{ title }}</h2>
            <p class="mt-1 text-sm text-sub">共 {{ slots.length }} 门课程，保存后默认仅自己可见。</p>
          </div>
          <button type="button" class="btn-sm" aria-label="关闭导入预览" :disabled="saving" @click="emit('close')">✕</button>
        </header>

        <ul v-if="notices.length" class="rounded-lg bg-amber-50 p-3 text-xs leading-5 text-amber-800">
          <li v-for="(notice, index) in notices" :key="index">· {{ notice }}</li>
        </ul>

        <div class="grid gap-3 sm:grid-cols-2">
          <label class="label sm:col-span-2">课表名称
            <input v-model="form.name" class="input mt-1" maxlength="255" required />
          </label>
          <label class="label">学期第一周周一（选填）
            <input v-model="form.term_start" type="date" class="input mt-1" />
          </label>
          <label class="label">第一节开始时间
            <input v-model="form.first_start" type="time" class="input mt-1" required />
          </label>
          <label class="label">每节课时长（分钟）
            <input v-model.number="form.lesson_minutes" type="number" class="input mt-1" min="15" max="180" required />
          </label>
          <label class="label">默认节间隔（分钟）
            <input v-model.number="form.break_minutes" type="number" class="input mt-1" min="0" max="180" required />
          </label>
        </div>

        <section class="overflow-hidden rounded-lg border border-primary-100">
          <div class="flex items-center justify-between border-b border-primary-100 bg-primary-50/70 px-3 py-2 text-xs font-semibold text-sub">
            <span>课程预览</span><span>{{ slots.length }} 门 · {{ lessonCount }} 节作息</span>
          </div>
          <div class="max-h-[32dvh] divide-y divide-primary-100/70 overflow-y-auto">
            <article v-for="(slot, index) in slots" :key="`${slot.weekday}-${slot.lesson_start}-${slot.name}-${index}`" class="grid grid-cols-[minmax(0,1fr)_auto] gap-3 px-3 py-2.5 text-sm">
              <div class="min-w-0">
                <p class="truncate font-semibold text-ink">{{ slot.name }}</p>
                <p class="mt-1 truncate text-xs text-sub">{{ slot.location || '未填写教室' }}<span v-if="slot.campus"> · {{ slot.campus }}</span></p>
              </div>
              <div class="text-right text-xs text-sub">
                <p class="font-semibold text-ink">{{ dayName(slot.weekday) }} · 第 {{ slot.lesson_start }}<template v-if="slot.lesson_end !== slot.lesson_start">–{{ slot.lesson_end }}</template> 节</p>
                <p class="mt-1">{{ slot.weeks.length ? `${slot.weeks[0]}–${slot.weeks[slot.weeks.length - 1]} 周` : '周次未识别' }}</p>
              </div>
            </article>
          </div>
        </section>

        <p class="rounded-md bg-primary-50 p-3 text-xs leading-5 text-sub">导入后仍可在作息设置中调整午休和晚间时间。公开课表前请再次核对课程、周次和教室。</p>
        <p v-if="validation || error" role="alert" class="text-sm text-red-700">{{ validation || error }}</p>
        <footer class="flex justify-end gap-2">
          <button type="button" class="btn-ghost" :disabled="saving" @click="emit('close')">取消导入</button>
          <button type="submit" class="btn-primary" :disabled="saving">{{ saving ? '正在保存…' : '确认并保存为私有课表' }}</button>
        </footer>
      </form>
    </div>
  </Teleport>
</template>

<style scoped>
.schedule-import-overlay { background: rgb(31 27 51 / 48%); backdrop-filter: blur(4px); }
.schedule-import-dialog { display: grid; width: min(44rem, calc(100vw - 1.5rem)); max-height: calc(100dvh - 1.5rem); gap: 1.1rem; overflow-y: auto; border-radius: 0.75rem; background: white; padding: 1.25rem; color: theme('colors.ink'); box-shadow: theme('boxShadow.glass'); }
@media (min-width: 640px) { .schedule-import-dialog { padding: 1.75rem; } }
</style>
