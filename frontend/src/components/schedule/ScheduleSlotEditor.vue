<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, reactive, ref } from 'vue'
import type { ScheduleSlot } from '@/types'
import { DAYS, formatWeeks, parseWeekSelection } from './calendar'

const props = defineProps<{
  initial: ScheduleSlot
  editing: boolean
  saving: boolean
  error: string
  termWeeks: number[]
  maxLesson: number
}>()
const emit = defineEmits<{ close: []; save: [slot: ScheduleSlot]; remove: [] }>()
const dialog = ref<HTMLDialogElement>()
const form = reactive({ ...props.initial })
const weeksText = ref(props.initial.weeks.length ? formatWeeks(props.initial.weeks) : '')
const validationError = ref('')
const confirmDelete = ref(false)
const title = computed(() => `${props.editing ? '编辑' : '添加'}${form.kind === 'event' ? '个人日程' : '课程'}`)
let returnFocus: HTMLElement | null = null
onMounted(() => {
  returnFocus = document.activeElement as HTMLElement | null
  dialog.value?.showModal()
})
onBeforeUnmount(() => {
  dialog.value?.close()
  returnFocus?.focus()
})

function submit() {
  if (props.saving) return
  validationError.value = ''
  try {
    if (!form.name.trim()) throw new Error('请填写名称')
    if (form.lesson_end < form.lesson_start) throw new Error('结束节次不能早于开始节次')
    emit('save', {
      ...form, name: form.name.trim(), location: form.location.trim(),
      campus: form.campus?.trim() || null, weeks: parseWeekSelection(weeksText.value),
    })
  } catch (error) {
    validationError.value = error instanceof Error ? error.message : '请检查填写内容'
  }
}

function quickWeeks(parity?: number) {
  const values = props.termWeeks.filter(week => parity === undefined || week % 2 === parity)
  weeksText.value = formatWeeks(values)
}
</script>

<template>
  <Teleport to="body">
    <dialog ref="dialog" class="slot-editor rounded-2xl bg-cream p-0 text-ink shadow-glass" aria-labelledby="slot-title" @cancel.prevent="!saving && emit('close')">
      <form class="space-y-5 p-5 sm:p-7" @submit.prevent="submit">
        <div class="flex items-center justify-between gap-3">
          <h2 id="slot-title" class="text-xl font-bold">{{ title }}</h2>
          <button type="button" class="btn-sm" :disabled="saving" aria-label="关闭编辑" @click="emit('close')">✕</button>
        </div>
        <fieldset :disabled="saving" class="space-y-4">
          <label class="label">类型
            <select v-model="form.kind" class="input mt-1"><option value="course">课程</option><option value="event">个人日程（参与忙闲计算）</option></select>
          </label>
          <label class="label">名称
            <input v-model="form.name" class="input mt-1" required maxlength="255" autofocus placeholder="例如：高等数学、社团拍摄、约饭" />
          </label>
          <div class="grid grid-cols-3 gap-3">
            <label class="label">星期<select v-model.number="form.weekday" class="input mt-1 !px-2"><option v-for="(day, i) in DAYS" :key="i" :value="i">{{ day }}</option></select></label>
            <label class="label">开始节次<select v-model.number="form.lesson_start" class="input mt-1 !px-2"><option v-for="n in maxLesson" :key="n" :value="n">第 {{ n }} 节</option></select></label>
            <label class="label">结束节次<select v-model.number="form.lesson_end" class="input mt-1 !px-2"><option v-for="n in maxLesson" :key="n" :value="n">第 {{ n }} 节</option></select></label>
          </div>
          <label class="label">发生周次
            <input v-model="weeksText" class="input mt-1" required placeholder="例如：1-16 或 1,3,5；仅第 8 周填 8" aria-describedby="week-help" />
          </label>
          <div class="flex flex-wrap gap-2">
            <button type="button" class="btn-xs" @click="quickWeeks()">课表全部周次</button>
            <button type="button" class="btn-xs" @click="quickWeeks(1)">单周</button>
            <button type="button" class="btn-xs" @click="quickWeeks(0)">双周</button>
          </div>
          <p id="week-help" class="text-xs leading-5 text-sub">单次安排只选一周，重复安排选多周。时间按课表节次计算；编辑影响所选的全部周次。</p>
          <div class="grid gap-3 sm:grid-cols-2">
            <label class="label">地点（选填）<input v-model="form.location" class="input mt-1" maxlength="255" placeholder="教室或活动地点" /></label>
            <label class="label">校区（选填）<input v-model="form.campus" class="input mt-1" maxlength="128" placeholder="例如：下沙校区" /></label>
          </div>
        </fieldset>
        <p class="rounded-xl bg-primary-50 p-3 text-xs leading-5 text-sub">
          {{ form.kind === 'event' ? '这段时间会被视为忙碌。公开课表后，圈友只看到“已有安排”和占用时间，看不到日程名称、地点或校区。' : '公开课表后，圈友可以看到这门课程的名称、地点和时间。' }}
        </p>
        <p v-if="validationError || error" role="alert" class="text-sm text-red-600">{{ validationError || error }}</p>
        <div v-if="confirmDelete" class="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          <p>删除此条目及其所有周次安排？</p>
          <div class="mt-3 flex gap-3">
            <button type="button" class="btn-sm-danger" :disabled="saving" @click="emit('remove')">确认删除</button>
            <button type="button" class="btn-sm" :disabled="saving" @click="confirmDelete = false">保留</button>
          </div>
        </div>
        <div class="flex flex-wrap justify-end gap-2">
          <button v-if="editing" type="button" class="btn-sm-danger mr-auto" :disabled="saving" @click="confirmDelete = true">删除此条</button>
          <button type="button" class="btn-ghost" :disabled="saving" @click="emit('close')">取消</button>
          <button type="submit" class="btn-primary" :disabled="saving">{{ saving ? '保存中…' : '保存' }}</button>
        </div>
      </form>
    </dialog>
  </Teleport>
</template>

<style scoped>
.slot-editor { width: min(36rem, calc(100vw - 2rem)); max-height: calc(100dvh - 2rem); overflow-y: auto; }
.slot-editor::backdrop { background: rgb(31 27 51 / 45%); backdrop-filter: blur(4px); }
</style>
