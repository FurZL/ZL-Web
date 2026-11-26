<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import ScheduleWeekGrid from '@/components/schedule/ScheduleWeekGrid.vue'
import ScheduleWeekPicker from '@/components/schedule/ScheduleWeekPicker.vue'
import ScheduleShelf from '@/components/schedule/ScheduleShelf.vue'
import type { AppointmentDetail, ScheduleRecord } from '@/types'
import { scheduleWeeks } from './calendar'

const props = defineProps<{
  schedules: ScheduleRecord[]
  activeSchedule: ScheduleRecord | null
  loading: boolean
  uploading: boolean
  uploadError: string
  creating: boolean
  addingLesson: boolean
  slotMoving: boolean
  metaSaving: boolean
  invitations: AppointmentDetail[]
  fileImportEnabled: boolean
  publicShareEnabled: boolean
}>()

const emit = defineEmits<{
  select: [schedule: ScheduleRecord]
  toggleShare: [schedule: ScheduleRecord]
  remove: [schedule: ScheduleRecord]
  upload: [file: File]
  clearError: []
  next: []
  edit: [index: number | null, weekday: number, lesson: number, week: number | null]
  timing: []
  create: [name: string]
  reload: []
  move: [index: number, weekday: number, lessonStart: number, lessonEnd: number]
  addLesson: []
  rename: [schedule: ScheduleRecord, name: string]
  archive: [schedule: ScheduleRecord]
  restore: [schedule: ScheduleRecord]
  reorder: [ids: string[]]
  invitation: [id: string]
}>()

const selectedWeek = ref<number | null>(null)
const weeks = computed(() => scheduleWeeks(props.activeSchedule?.slots ?? []))

watch(() => props.activeSchedule?.id, () => {
  selectedWeek.value = null
})

function onDrop(e: DragEvent) {
  if (props.uploading) return
  const f = e.dataTransfer?.files?.[0]
  if (f) emit('upload', f)
}

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  const f = input.files?.[0]
  if (f) emit('upload', f)
  input.value = ''
}
</script>

<template>
  <div class="mt-8 grid gap-5 xl:grid-cols-[minmax(0,1fr)_18rem]">
    <section class="glass-card min-w-0 p-5 sm:p-7">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p class="text-xs font-semibold uppercase tracking-[0.18em] text-primary-500">My timetable</p>
          <h2 class="mt-1 text-xl font-bold text-ink">我的课表</h2>
          <p class="mt-1 text-sm text-sub">从课表架挑一张使用，再找一位课搭子。</p>
        </div>
        <div v-if="activeSchedule" class="rounded-2xl bg-primary-50 px-3 py-2 text-right">
          <p class="text-lg font-bold text-primary-700">{{ activeSchedule.slots.length }}</p>
          <p class="text-[11px] text-primary-500">条课程 / 日程</p>
        </div>
      </div>

      <div v-if="loading" class="mt-6 space-y-3">
        <div v-for="i in 3" :key="i" class="h-16 animate-pulse rounded-2xl bg-primary-50/80"></div>
      </div>

      <template v-else>
        <ScheduleShelf
          :schedules="schedules"
          :active-id="activeSchedule?.id ?? null"
          :creating="creating"
          :busy="metaSaving"
          :file-import-enabled="fileImportEnabled"
          :public-share-enabled="publicShareEnabled"
          @select="emit('select', $event)"
          @create="(name) => emit('create', name)"
          @rename="(schedule, name) => emit('rename', schedule, name)"
          @archive="(schedule) => emit('archive', schedule)"
          @restore="(schedule) => emit('restore', schedule)"
          @toggle-share="(schedule) => emit('toggleShare', schedule)"
          @remove="(schedule) => emit('remove', schedule)"
          @reorder="(ids) => emit('reorder', ids)"
        />

        <div v-if="activeSchedule" class="mt-6 space-y-4">
          <ScheduleWeekPicker v-model="selectedWeek" :weeks="weeks" />
          <div class="flex flex-wrap items-center justify-between gap-3">
            <p class="text-xs text-sub">点空白格新增，点卡片编辑；拖动卡片换时间段，拖卡片底部调整节数。网格底部可直接添加一节。</p>
            <div class="flex flex-wrap gap-2">
              <button type="button" class="btn-sm-primary cursor-pointer" @click="emit('timing')">⚙ 作息设置</button>
              <button type="button" class="btn-sm-primary" @click="emit('edit', null, 0, 1, selectedWeek)">＋ 添加课程 / 日程</button>
            </div>
          </div>
          <ScheduleWeekGrid :slots="activeSchedule.slots" :timing="activeSchedule.timing" :week="selectedWeek" editable
            :adding-lesson="addingLesson" :slot-moving="slotMoving" :invitations="invitations"
            @add="(day, lesson) => emit('edit', null, day, lesson, selectedWeek)"
            @edit="index => emit('edit', index, 0, 1, selectedWeek)"
            @move="(index, weekday, start, end) => emit('move', index, weekday, start, end)"
            @invitation="emit('invitation', $event)"
            @add-lesson="emit('addLesson')" />
          <p class="text-xs text-sub">绿色虚线卡片为个人日程。作息设置只影响当前课表，不会改变其他学期。</p>
        </div>

        <div
          v-else
          class="mt-5 rounded-2xl border border-dashed border-primary-200 bg-primary-50/40 px-4 py-6 text-center text-sm text-sub"
        >
          {{ fileImportEnabled ? '从课表架选择一张课表开始编辑，或新建、恢复、上传一张课表。' : '从课表架选择一张课表开始编辑，或新建、恢复一张课表。' }}
        </div>

        <div class="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-primary-100/70 pt-4">
          <p class="max-w-lg text-xs leading-5 text-faint">
            公开后，圈友可看到课程详情和日程占用时间。个人日程名称、地点和校区仅自己可见，原始文件保持私有。
          </p>
          <div class="flex gap-2">
            <button class="btn-sm" type="button" @click="emit('reload')">重新加载</button>
            <button class="btn-primary !px-5 !py-2 text-xs" type="button" :disabled="!activeSchedule" @click="emit('next')">
              找课搭子 <span aria-hidden="true">→</span>
            </button>
          </div>
        </div>
      </template>
    </section>

    <aside class="glass-card h-fit p-5 sm:p-6">
      <div class="flex items-start gap-3">
        <span class="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-blush/20 text-xl">＋</span>
        <div>
          <p class="text-xs font-semibold uppercase tracking-[0.18em] text-blush">Add a schedule</p>
          <h2 class="mt-1 text-lg font-bold text-ink">添加新课表</h2>
        </div>
      </div>

      <label
        v-if="fileImportEnabled"
        class="mt-5 flex min-h-[15rem] cursor-pointer flex-col items-center justify-center rounded-3xl border-2 border-dashed px-5 text-center transition"
        :class="uploadError ? 'border-red-300 bg-red-50/60' : 'border-primary-200 bg-white/40 hover:border-primary-400 hover:bg-primary-50/60'"
        @dragover.prevent
        @drop.prevent="onDrop"
      >
        <input ref="fileInput" type="file" accept=".ics,.txt,.pdf" class="hidden" :disabled="uploading" @change="onFileChange" />
        <div v-if="uploading" class="flex flex-col items-center">
          <div class="spinner"></div>
          <p class="mt-4 text-sm font-medium text-sub">正在解析课表…</p>
        </div>
        <div v-else-if="uploadError" class="flex flex-col items-center">
          <div class="flex h-12 w-12 items-center justify-center rounded-2xl bg-red-100 text-xl text-red-600">!</div>
          <p class="mt-3 text-sm font-semibold text-red-600">{{ uploadError }}</p>
          <p class="mt-1 text-xs text-faint">点击重新选择文件</p>
        </div>
        <div v-else class="flex flex-col items-center">
          <div class="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary-50 text-2xl">📄</div>
          <p class="mt-4 text-sm font-semibold text-ink">拖入文件，或点击选择</p>
          <p class="mt-2 text-xs leading-5 text-faint">支持 .ics / .txt / .pdf<br />PDF 只解析预览，不保存原文件</p>
        </div>
      </label>
      <p v-else class="mt-5 text-sm text-sub">文件导入暂不可用。</p>

      <div class="mt-5 space-y-2 rounded-2xl bg-ink/[0.04] p-4 text-xs leading-5 text-sub">
        <p class="font-semibold text-ink">上传前记得确认</p>
        <p v-if="fileImportEnabled">· 上传 ICS / TXT / PDF，或使用浏览器扩展读取教务课表</p>
        <p v-else>· 可使用浏览器扩展读取教务课表</p>
        <p>· 课表中的教室信息越完整，对比越准确</p>
        <p v-if="publicShareEnabled">· 课表可随时切换“仅自己 / 公开中”</p>
      </div>

      <section class="mt-5 border-t border-primary-100/70 pt-4">
        <h3 class="text-sm font-semibold text-ink">教务系统辅助导入</h3>
        <p class="mt-1 text-xs leading-5 text-sub">在已登录的教务个人课表页点击“啫喱小站课表助手”，发送后回到这里预览并确认保存。</p>
      </section>

      <button v-if="uploadError" type="button" class="btn-ghost mt-4 w-full !py-2 text-xs" @click="emit('clearError')">
        清除提示
      </button>
    </aside>
  </div>
</template>
