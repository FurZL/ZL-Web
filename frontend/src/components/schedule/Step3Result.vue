<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import ScheduleWeekGrid from '@/components/schedule/ScheduleWeekGrid.vue'
import ScheduleWeekPicker from '@/components/schedule/ScheduleWeekPicker.vue'
import ScheduleInvitePopover from '@/components/schedule/ScheduleInvitePopover.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import type { AppointmentDetail, CompareFreeSlot, ScheduleCompareResult, ScheduleRecord } from '@/types'
import { scheduleWeeks } from './calendar'

const props = defineProps<{
  mySchedule: ScheduleRecord | null
  partner: ScheduleRecord | null
  result: ScheduleCompareResult | null
  week: number | null
  loading: boolean
  error: string
  invite: AppointmentDetail | null
  inviting: boolean
  inviteError: string
}>()

const emit = defineEmits<{
  back: []
  week: [value: number | null]
  invite: [payload: { free: CompareFreeSlot; week: number; title: string }]
  refreshInvite: []
}>()
const selectedWeek = computed({
  get: () => props.week,
  set: value => emit('week', value),
})
const weeks = computed(() => scheduleWeeks([...(props.mySchedule?.slots ?? []), ...(props.partner?.slots ?? [])]))

const freeCount = computed(() => props.result?.both_free.length ?? 0)
const sameRoomCount = computed(() => props.result?.same_classroom.length ?? 0)
const overlapCount = computed(() => props.result?.overlaps.length ?? 0)

type CellRect = { top: number; left: number; right: number; bottom: number; width: number; height: number }
type HoverCell = { weekday: number; lesson: number; rect: CellRect }
type PinnedCell = { weekday: number; lesson_start: number; lesson_end: number; rect: CellRect }

const inviteWeek = ref<number | null>(null)
const effectiveInviteWeek = computed(() => props.week ?? inviteWeek.value)
const hoverCell = ref<HoverCell | null>(null)
const pinnedCell = ref<PinnedCell | null>(null)
const activeCell = computed<PinnedCell | null>(() => {
  if (pinnedCell.value) return pinnedCell.value
  if (!hoverCell.value) return null
  return {
    weekday: hoverCell.value.weekday,
    lesson_start: hoverCell.value.lesson,
    lesson_end: hoverCell.value.lesson,
    rect: hoverCell.value.rect,
  }
})
let hideTimer: ReturnType<typeof setTimeout> | undefined

const canInvite = computed(() => Boolean(
  props.partner?.owner?.username
  && props.mySchedule?.timing?.term_start
  && effectiveInviteWeek.value !== null
  && props.result?.both_free.length
  && !props.inviting
  && (!props.invite || props.invite.status !== 'pending'),
))

function defaultInviteWeek(): number | null {
  if (!weeks.value.length) return null
  const term = props.mySchedule?.timing?.term_start
  if (!term) return weeks.value[0]
  const today = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Shanghai' }).format(new Date())
  const start = new Date(`${term}T00:00:00+08:00`).getTime()
  const current = new Date(`${today}T00:00:00+08:00`).getTime()
  const week = Math.floor((current - start) / 86_400_000 / 7) + 1
  if (weeks.value.includes(week)) return week
  return weeks.value[0]
}

watch([() => props.week, weeks, () => props.mySchedule?.timing?.term_start], () => {
  if (props.week !== null) {
    inviteWeek.value = props.week
  } else if (inviteWeek.value === null || !weeks.value.includes(inviteWeek.value)) {
    inviteWeek.value = defaultInviteWeek()
  }
}, { immediate: true })

watch(() => props.invite?.id, () => {
  if (props.invite) closePopover()
})

watch([effectiveInviteWeek, () => props.result], () => closePopover())

function clearHideTimer() {
  if (hideTimer) clearTimeout(hideTimer)
  hideTimer = undefined
}

function inviteFree(free: CompareFreeSlot, title: string) {
  if (!canInvite.value || effectiveInviteWeek.value === null) return
  emit('invite', { free, week: effectiveInviteWeek.value, title })
}

function onFreeHover(cell: HoverCell) {
  if (!canInvite.value || pinnedCell.value) return
  clearHideTimer()
  hoverCell.value = cell
}

function onFreeHoverEnd() {
  if (pinnedCell.value) return
  clearHideTimer()
  hideTimer = setTimeout(() => { hoverCell.value = null }, 140)
}

function onFreePin(cell: PinnedCell) {
  if (!canInvite.value) return
  clearHideTimer()
  pinnedCell.value = cell
}

function onPopoverHover(over: boolean) {
  if (over) {
    clearHideTimer()
    return
  }
  if (!pinnedCell.value) onFreeHoverEnd()
}

function closePopover() {
  clearHideTimer()
  hoverCell.value = null
  pinnedCell.value = null
}

function sendPopover(title: string) {
  const cell = activeCell.value
  if (!cell) return
  inviteFree({
    weekday: cell.weekday,
    lesson_start: cell.lesson_start,
    lesson_end: cell.lesson_end,
  }, title)
}

const activeBlock = computed(() => activeCell.value ? {
  weekday: activeCell.value.weekday,
  lesson_start: activeCell.value.lesson_start,
  lesson_end: activeCell.value.lesson_end,
} : null)

const inviteTime = computed(() => {
  const start = props.invite?.fixed?.starts_at
  const end = props.invite?.fixed?.ends_at
  if (!start || !end) return ''
  const date = new Intl.DateTimeFormat('zh-CN', {
    timeZone: 'Asia/Shanghai', month: 'numeric', day: 'numeric', weekday: 'short',
  }).format(new Date(start))
  const clock = (value: string) => new Intl.DateTimeFormat('zh-CN', {
    timeZone: 'Asia/Shanghai', hour: '2-digit', minute: '2-digit', hour12: false,
  }).format(new Date(value))
  return `${date} ${clock(start)}–${clock(end)}`
})
</script>

<template>
  <div class="mt-8 space-y-5">
    <section class="glass-card p-5 sm:p-7">
      <div class="flex flex-wrap items-center gap-3">
        <div class="flex items-center gap-2.5">
          <UserAvatar :name="'我'" :size="42" />
          <div><p class="text-sm font-bold text-ink">我的课表</p><p class="text-xs text-faint">{{ mySchedule?.original_name || '当前课表' }}</p></div>
        </div>
        <span class="rounded-full bg-primary-50 px-3 py-1 text-xs font-bold text-primary-600">×</span>
        <div class="flex items-center gap-2.5">
          <UserAvatar :name="partner?.owner?.display_name ?? ''" :size="42" />
          <div><p class="text-sm font-bold text-ink">{{ partner?.owner?.display_name }}</p><p class="text-xs text-faint">@{{ partner?.owner?.username }}</p></div>
        </div>
        <button class="btn-ghost ml-auto !px-4 !py-2 text-xs" type="button" :disabled="loading" @click="emit('back')">重新选择</button>
      </div>

      <p class="mt-5 text-sm text-sub">{{ week === null ? '全学期总览：空闲时段排除任意周已记录的课程和日程' : `第 ${week} 周：已计入双方的课程和个人日程` }}</p>
      <div v-if="result" class="mt-3 flex flex-wrap gap-2 text-[11px]">
        <span class="rounded-full bg-emerald-50 px-3 py-1 font-semibold text-emerald-700">共同空闲 {{ freeCount }} 段</span>
        <span class="rounded-full bg-amber-50 px-3 py-1 font-semibold text-amber-700">同教室 {{ sameRoomCount }} 节</span>
        <span class="rounded-full bg-blush/10 px-3 py-1 font-semibold text-[#a44e79]">冲突 {{ overlapCount }} 处</span>
        <span class="rounded-full bg-primary-50 px-3 py-1 text-primary-700">拖动空闲格自由选时间段</span>
      </div>
    </section>

    <section class="glass-card min-w-0 p-5 sm:p-7">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p class="text-xs font-semibold uppercase tracking-[0.18em] text-primary-500">Together view</p>
          <h2 class="mt-1 text-xl font-bold text-ink">你们的时间地图</h2>
          <p class="mt-1 text-sm text-sub">点表头选中一列，再点绿色空闲格发出约定；悬停或点按列会浮起绿框。同教室用琥珀色小圆点标在网格里。</p>
        </div>
        <div class="flex flex-wrap gap-2 text-[11px] text-sub">
          <span class="flex items-center gap-1.5 rounded-full bg-primary-50 px-2.5 py-1"><i class="h-2.5 w-2.5 rounded-full bg-primary"></i>我的安排</span>
          <span class="flex items-center gap-1.5 rounded-full bg-blush/15 px-2.5 py-1"><i class="h-2.5 w-2.5 rounded-full bg-blush"></i>对方的安排</span>
        </div>
      </div>

      <div v-if="week === null && weeks.length" class="mt-3 inline-flex flex-wrap items-center gap-2 rounded-full bg-primary-50/60 px-3 py-1.5">
        <label class="text-xs font-semibold text-primary-700" for="invite-week">约定周次</label>
        <select id="invite-week" v-model="inviteWeek" class="input !w-auto !py-1 text-xs">
          <option v-for="item in weeks" :key="item" :value="item">第 {{ item }} 周</option>
        </select>
        <span class="text-[11px] text-sub">选中后加入的是具体日期，不是每周重复。</span>
      </div>
      <p v-if="!mySchedule?.timing?.term_start" class="mt-4 rounded-xl bg-amber-50 px-4 py-3 text-xs leading-5 text-amber-800">
        先在我的课表“作息设置”里填写学期第一周周一，才能把空闲格子约成具体日程。
      </p>

      <div v-if="invite" role="status" class="mt-4 rounded-xl border px-4 py-3 text-sm leading-6"
        :class="invite.status === 'confirmed' ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : 'border-amber-200 bg-amber-50 text-amber-800'">
        <template v-if="invite.status === 'confirmed'">已约定 {{ inviteTime }}，双方日程已加入「{{ invite.title }}」。</template>
        <template v-else-if="invite.status === 'pending'">已向 {{ partner?.owner?.display_name || '对方' }} 发出约定：{{ inviteTime }}，等待对方同意；同意后会自动加入双方日程。
          <button type="button" class="btn-xs ml-2" :disabled="inviting" @click="emit('refreshInvite')">刷新状态</button>
        </template>
        <template v-else>这次约定状态：{{ invite.status }}。</template>
      </div>
      <p v-if="inviteError" role="alert" class="mt-3 text-sm text-red-600">{{ inviteError }}</p>

      <div class="mt-5 space-y-4">
        <ScheduleWeekPicker v-model="selectedWeek" :weeks="weeks" compact />
        <p v-if="loading" role="status" class="text-sm text-sub">正在读取最新课表并计算…</p>
        <div v-else-if="error" role="alert" class="text-sm text-red-600">
          {{ error }} <button type="button" class="btn-sm" @click="emit('week', week)">重试</button>
        </div>
        <ScheduleWeekGrid
          v-else-if="result"
          :slots="mySchedule?.slots ?? []"
          :timing="mySchedule?.timing"
          :partner-slots="partner?.slots ?? []"
          :partner-timing="partner?.timing"
          :compare-result="result"
          :week="selectedWeek"
          :free-selectable="canInvite"
          comparing
          @free-hover="onFreeHover"
          @free-hover-end="onFreeHoverEnd"
          @free-pin="onFreePin"
        />
      </div>

      <div class="mt-5 flex flex-wrap gap-x-5 gap-y-2 text-xs text-sub">
        <span class="flex items-center gap-1.5"><i class="h-3 w-3 rounded bg-emerald-100 ring-1 ring-emerald-300"></i>双方空闲（点按发起邀请）</span>
        <span class="flex items-center gap-1.5"><i class="h-3 w-3 rounded bg-amber-100 ring-1 ring-amber-300"></i>同教室同时间</span>
        <span class="flex items-center gap-1.5"><i class="h-3 w-3 rounded bg-blush/20 ring-1 ring-blush/40"></i>双方都有安排</span>
        <span class="flex items-center gap-1.5"><i class="h-3 w-3 rounded bg-primary-100 ring-1 ring-primary-300"></i>只有一方有安排</span>
        <span>斜纹：不同周占用 · 虚线卡片：个人日程</span>
      </div>
    </section>

    <ScheduleInvitePopover
      v-if="activeCell && activeBlock && effectiveInviteWeek !== null"
      :cell="activeBlock"
      :rect="activeCell.rect"
      :week="effectiveInviteWeek"
      :partner-name="partner?.owner?.display_name ?? partner?.owner?.username ?? ''"
      :pinned="Boolean(pinnedCell)"
      :sending="inviting"
      :error="inviteError"
      @send="sendPopover"
      @close="closePopover"
      @hover="onPopoverHover"
    />
  </div>
</template>
