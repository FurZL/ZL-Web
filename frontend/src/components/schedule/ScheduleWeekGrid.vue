<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import type { AppointmentDetail, ScheduleCompareResult, ScheduleSlot, ScheduleTiming } from '@/types'
import { DAYS, DEFAULT_LESSON_COUNT, MAX_LESSON, formatWeeks, nextSchedulePeriod, periodSegment, periodSegmentLabel } from './calendar'

const props = withDefaults(
  defineProps<{
    slots: ScheduleSlot[]
    timing?: ScheduleTiming | null
    partnerSlots?: ScheduleSlot[]
    partnerTiming?: ScheduleTiming | null
    compareResult?: ScheduleCompareResult | null
    week?: number | null
    compact?: boolean
    editable?: boolean
    comparing?: boolean
    addingLesson?: boolean
    slotMoving?: boolean
    invitations?: AppointmentDetail[]
    freeSelectable?: boolean
  }>(),
  {
    partnerSlots: () => [],
    timing: null,
    partnerTiming: null,
    compareResult: null,
    week: null,
    compact: false,
    editable: false,
    comparing: false,
    addingLesson: false,
    slotMoving: false,
    invitations: () => [],
    freeSelectable: false,
  },
)

const days = DAYS
const hoveredDay = ref<number | null>(null)
const selectedDay = ref<number | null>(null)
const dragging = ref(false)
const dragStart = ref<{ day: number; lesson: number } | null>(null)
const dragEnd = ref<{ day: number; lesson: number } | null>(null)
const suppressClick = ref(false)
const activeDay = computed(() => props.freeSelectable ? (hoveredDay.value ?? selectedDay.value) : null)
const selectedRange = computed(() => {
  if (!dragStart.value || !dragEnd.value) return null
  return {
    day: dragStart.value.day,
    start: Math.min(dragStart.value.lesson, dragEnd.value.lesson),
    end: Math.max(dragStart.value.lesson, dragEnd.value.lesson),
  }
})

function isSelectedFree(day: number, lesson: number) {
  const range = selectedRange.value
  return Boolean(range && range.day === day && lesson >= range.start && lesson <= range.end)
}

function onDayEnter(day: number) {
  if (props.freeSelectable) hoveredDay.value = day
}

function selectDay(day: number) {
  if (!props.freeSelectable) return
  selectedDay.value = selectedDay.value === day ? null : day
}

function cellComponent(cell: { kind: CellKind }) {
  if (props.editable) return 'button'
  return props.freeSelectable && cell.kind === 'both-free' ? 'button' : 'div'
}

function rectOf(cell: Element | null): CellRect | null {
  if (!cell) return null
  const rect = cell.getBoundingClientRect()
  return { top: rect.top, left: rect.left, right: rect.right, bottom: rect.bottom, width: rect.width, height: rect.height }
}

function onCellClick(cell: { day: number; lesson: number; kind: CellKind }, event?: MouseEvent) {
  if (props.editable) {
    emit('add', cell.day, cell.lesson)
    return
  }
  if (!props.freeSelectable) return
  if (suppressClick.value) {
    suppressClick.value = false
    return
  }
  selectedDay.value = cell.day
  if (cell.kind === 'both-free') {
    const rect = rectOf(event?.currentTarget as Element | null)
    if (rect) emit('freePin', { weekday: cell.day, lesson_start: cell.lesson, lesson_end: cell.lesson, rect })
  }
}

function onCellPointerEnter(cell: { day: number; lesson: number; kind: CellKind }, event: PointerEvent) {
  onDayEnter(cell.day)
  if (dragging.value || !props.freeSelectable || cell.kind !== 'both-free') return
  const rect = rectOf(event.currentTarget as Element | null)
  if (rect) emit('freeHover', { weekday: cell.day, lesson: cell.lesson, rect })
}

function onCellPointerLeave(cell: { kind: CellKind }) {
  if (props.freeSelectable && cell.kind === 'both-free') emit('freeHoverEnd')
}

function onCellPointerDown(cell: { day: number; lesson: number; kind: CellKind }, event: PointerEvent) {
  if (props.editable || !props.freeSelectable || cell.kind !== 'both-free') return
  if (event.pointerType === 'mouse' && event.button !== 0) return
  event.preventDefault()
  dragging.value = true
  dragStart.value = { day: cell.day, lesson: cell.lesson }
  dragEnd.value = { day: cell.day, lesson: cell.lesson }
  selectedDay.value = cell.day
  hoveredDay.value = cell.day
  suppressClick.value = true
  emit('freeHoverEnd')
  window.addEventListener('pointermove', onFreeDragMove, { passive: false })
  window.addEventListener('pointerup', onFreeDragEnd)
  window.addEventListener('pointercancel', onFreeDragCancel)
}

function onFreeDragMove(event: PointerEvent) {
  if (!dragStart.value) return
  event.preventDefault()
  const element = document.elementFromPoint(event.clientX, event.clientY)?.closest<HTMLElement>('.schedule-cell')
  if (!element) return
  const day = Number(element.dataset.day)
  const lesson = Number(element.dataset.lesson)
  if (!Number.isInteger(day) || !Number.isInteger(lesson) || day !== dragStart.value.day) return
  if (!element.classList.contains('schedule-cell--both-free')) return
  const start = dragStart.value.lesson
  const step = lesson >= start ? 1 : -1
  let last = start
  for (let current = start; current !== lesson + step; current += step) {
    if (cellKind(day, current) !== 'both-free') break
    last = current
  }
  dragEnd.value = { day, lesson: last }
}

function onFreeDragEnd() {
  window.removeEventListener('pointermove', onFreeDragMove)
  window.removeEventListener('pointerup', onFreeDragEnd)
  window.removeEventListener('pointercancel', onFreeDragCancel)
  dragging.value = false
  const start = dragStart.value
  const end = dragEnd.value
  dragStart.value = null
  dragEnd.value = null
  if (!start || !end) return
  const lessonStart = Math.min(start.lesson, end.lesson)
  const lessonEnd = Math.max(start.lesson, end.lesson)
  const cell = document.querySelector<HTMLElement>(
    `.schedule-cell[data-day="${start.day}"][data-lesson="${lessonStart}"]`,
  )
  const rect = rectOf(cell)
  if (rect) emit('freePin', { weekday: start.day, lesson_start: lessonStart, lesson_end: lessonEnd, rect })
  setTimeout(() => { suppressClick.value = false }, 0)
}

function onFreeDragCancel() {
  window.removeEventListener('pointermove', onFreeDragMove)
  window.removeEventListener('pointerup', onFreeDragEnd)
  window.removeEventListener('pointercancel', onFreeDragCancel)
  dragging.value = false
  dragStart.value = null
  dragEnd.value = null
  setTimeout(() => { suppressClick.value = false }, 0)
}

onBeforeUnmount(() => {
  window.removeEventListener('pointermove', onFreeDragMove)
  window.removeEventListener('pointerup', onFreeDragEnd)
  window.removeEventListener('pointercancel', onFreeDragCancel)
})

const displayWeek = computed(() => {
  if (props.week !== null) return props.week
  const termStart = props.timing?.term_start
  if (!termStart) return null
  const today = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Shanghai' }).format(new Date())
  const term = new Date(`${termStart}T00:00:00+08:00`).getTime()
  const current = new Date(`${today}T00:00:00+08:00`).getTime()
  if (!Number.isFinite(term) || !Number.isFinite(current)) return null
  const week = Math.floor((current - term) / 86_400_000 / 7) + 1
  return Math.min(53, Math.max(1, week))
})

const dateLabels = computed(() => {
  const termStart = props.timing?.term_start
  const week = displayWeek.value
  if (!termStart || week === null) return []
  const term = new Date(`${termStart}T00:00:00+08:00`).getTime()
  if (!Number.isFinite(term)) return []
  return days.map((_, index) => {
    const date = new Date(term + ((week - 1) * 7 + index) * 86_400_000)
    const parts = new Intl.DateTimeFormat('en-US', {
      timeZone: 'Asia/Shanghai', month: '2-digit', day: '2-digit',
    }).formatToParts(date)
    const month = Number(parts.find(part => part.type === 'month')?.value)
    const day = Number(parts.find(part => part.type === 'day')?.value)
    return `${month}/${day}`
  })
})

function dateTitle(index: number) {
  if (!dateLabels.value.length) return undefined
  return `第 ${displayWeek.value} 周 · ${dateLabels.value[index]}`
}
const emit = defineEmits<{
  add: [weekday: number, lesson: number]
  edit: [index: number]
  move: [index: number, weekday: number, lessonStart: number, lessonEnd: number]
  addLesson: []
  invitation: [id: string]
  freeHover: [cell: { weekday: number; lesson: number; rect: CellRect }]
  freeHoverEnd: []
  freePin: [cell: { weekday: number; lesson_start: number; lesson_end: number; rect: CellRect }]
}>()

type CellKind = 'both-busy' | 'one-busy' | 'both-free' | 'same-room' | 'different-weeks'
type CellRect = { top: number; left: number; right: number; bottom: number; width: number; height: number }
type CourseSide = 'mine' | 'partner' | 'single'
interface CourseBlock {
  key: string
  slot: ScheduleSlot
  index: number
  lane: number
  lanes: number
  side: CourseSide
}

function visibleInWeek(slot: ScheduleSlot) {
  return props.week === null || !slot.weeks.length || slot.weeks.includes(props.week)
}

const visibleMine = computed(() => props.slots.filter(visibleInWeek))
const visiblePartner = computed(() => props.partnerSlots.filter(visibleInWeek))
const compareMode = computed(() => props.comparing)
const lessonCount = computed(() => {
  const slotCounts = [...props.slots, ...props.partnerSlots].map(slot => slot.lesson_end)
  const timingCounts = [props.timing?.periods.length ?? 0, props.partnerTiming?.periods.length ?? 0]
  const count = Math.max(...slotCounts, ...timingCounts, 0)
  return Math.min(MAX_LESSON, count || DEFAULT_LESSON_COUNT)
})

const invitationBlocks = computed(() => {
  const week = props.week ?? displayWeek.value
  return props.invitations
    .filter(invitation => invitation.mode === 'fixed'
      && invitation.status === 'pending'
      && invitation.fixed?.weekday != null
      && invitation.fixed?.lesson_start != null)
    .filter(invitation => week === null || invitation.fixed?.week === week)
    .map(invitation => {
      const fixed = invitation.fixed!
      const start = Math.max(1, Math.min(lessonCount.value, fixed.lesson_start!))
      const end = Math.max(start, Math.min(lessonCount.value, fixed.lesson_end ?? start))
      return {
        invitation,
        style: {
          gridColumn: String(fixed.weekday! + 2),
          gridRow: `${start + 1} / span ${end - start + 1}`,
        },
      }
    })
})

function invitationHint(invitation: AppointmentDetail) {
  return invitation.viewer_participant.role === 'organizer' ? '等待对方接受' : '待你接受'
}

const displayTiming = computed(() => props.timing?.periods?.length ? props.timing : props.partnerTiming)

function periodAt(lesson: number) {
  return displayTiming.value?.periods[lesson - 1] ?? null
}

function segmentLabelAt(lesson: number) {
  const current = periodAt(lesson)
  if (!current) return ''
  const previous = lesson > 1 ? periodAt(lesson - 1) : null
  const currentSegment = periodSegment(displayTiming.value, lesson - 1)
  const previousSegment = previous ? periodSegment(displayTiming.value, lesson - 2) : null
  return !previous || currentSegment !== previousSegment ? periodSegmentLabel(currentSegment) : ''
}

function segmentClassAt(lesson: number) {
  return `schedule-time--${periodSegment(displayTiming.value, lesson - 1)}`
}

function segmentStartsAt(lesson: number) {
  return Boolean(segmentLabelAt(lesson) && lesson > 1)
}

function slotCovers(slot: ScheduleSlot, weekday: number, lesson: number) {
  return slot.weekday === weekday && lesson >= slot.lesson_start && lesson <= slot.lesson_end
}

function sameRoomAt(weekday: number, lesson: number) {
  return (props.compareResult?.same_classroom ?? []).some(
    (item) =>
      item.weekday === weekday &&
      visibleInWeek(item.a) &&
      visibleInWeek(item.b) &&
      slotCovers(item.a, weekday, lesson) &&
      slotCovers(item.b, weekday, lesson),
  )
}

function cellKind(day: number, lesson: number): CellKind {
  const mine = visibleMine.value.some((slot) => slotCovers(slot, day, lesson))
  const theirs = visiblePartner.value.some((slot) => slotCovers(slot, day, lesson))

  if (!compareMode.value) return mine ? 'one-busy' : 'both-free'
  if (mine && theirs) {
    if (sameRoomAt(day, lesson)) return 'same-room'
    const overlap = (props.compareResult?.overlaps ?? []).some(item =>
      slotCovers(item.a, day, lesson) && slotCovers(item.b, day, lesson))
    return overlap ? 'both-busy' : 'different-weeks'
  }
  if (mine || theirs) return 'one-busy'
  return 'both-free'
}

const cells = computed(() => {
  const result: { day: number; lesson: number; kind: CellKind; segmentStart: boolean }[] = []
  for (let lesson = 1; lesson <= lessonCount.value; lesson += 1) {
    for (let day = 0; day < days.length; day += 1) {
      result.push({ day, lesson, kind: cellKind(day, lesson), segmentStart: segmentStartsAt(lesson) })
    }
  }
  return result
})

function blockStyle(course: { slot: ScheduleSlot; side: CourseSide; lane: number; lanes: number }) {
  const { slot, side, lane, lanes } = course
  const start = Math.max(1, Math.min(lessonCount.value, slot.lesson_start))
  const end = Math.max(start, Math.min(lessonCount.value, slot.lesson_end))
  return {
    gridColumn: String(slot.weekday + 2),
    gridRow: `${start + 1} / span ${end - start + 1}`,
    width: `calc(${(compareMode.value ? 50 : 100) / lanes}% - 0.36rem)`,
    marginLeft: `calc(${(side === 'partner' ? 50 : 0) + lane * (compareMode.value ? 50 : 100) / lanes}% + 0.18rem)`,
  }
}

const courseBlocks = computed(() => {
  const mine = props.slots.map((slot, index) => ({
    key: `mine-${index}-${slot.name}`,
    slot,
    index,
    lane: 0,
    lanes: 1,
    side: (compareMode.value ? 'mine' : 'single') as CourseSide,
  })).filter(item => visibleInWeek(item.slot))
  const partner = props.partnerSlots.map((slot, index) => ({
    key: `partner-${index}-${slot.name}`,
    slot,
    index,
    lane: 0,
    lanes: 1,
    side: 'partner' as CourseSide,
  })).filter(item => visibleInWeek(item.slot))
  const blocks = [...mine, ...partner]
  // 同一天/同一人的重叠时段分列，保证每条卡片都可以点击。
  for (let day = 0; day < 7; day++) {
    for (const side of ['single', 'mine', 'partner']) {
      const group = blocks.filter(b => b.slot.weekday === day && b.side === side)
        .sort((a, b) => a.slot.lesson_start - b.slot.lesson_start)
      const ends: number[] = []
      for (const block of group) {
        let lane = ends.findIndex(end => end < block.slot.lesson_start)
        if (lane === -1) lane = ends.length
        ends[lane] = block.slot.lesson_end
        block.lane = lane
      }
      for (const block of group) block.lanes = ends.length
    }
  }
  return blocks
})

interface CompareBlock {
  key: string
  day: number
  start: number
  end: number
  mine: ScheduleSlot[]
  partner: ScheduleSlot[]
  sameRoom: boolean
}

function compareSlotSignature(slot: ScheduleSlot) {
  return `${slot.name}|${slot.location}|${slot.lesson_start}|${slot.lesson_end}|${slot.weeks.join(',')}`
}

const compareBlocks = computed(() => {
  const result: CompareBlock[] = []
  for (let day = 0; day < 7; day += 1) {
    let current: CompareBlock | null = null
    for (let lesson = 1; lesson <= lessonCount.value; lesson += 1) {
      const mine = visibleMine.value.filter(slot => (
        slot.weekday === day && lesson >= slot.lesson_start && lesson <= slot.lesson_end
      ))
      const partner = visiblePartner.value.filter(slot => (
        slot.weekday === day && lesson >= slot.lesson_start && lesson <= slot.lesson_end
      ))
      if (!mine.length && !partner.length) {
        if (current) result.push(current)
        current = null
        continue
      }
      const signature = `${mine.map(compareSlotSignature).sort().join(';')}::${partner.map(compareSlotSignature).sort().join(';')}`
      if (current && current.end === lesson - 1 && current.key === `${day}-${signature}`) {
        current.end = lesson
        current.sameRoom ||= sameRoomAt(day, lesson)
      } else {
        if (current) result.push(current)
        current = {
          key: `${day}-${signature}`,
          day,
          start: lesson,
          end: lesson,
          mine,
          partner,
          sameRoom: sameRoomAt(day, lesson),
        }
      }
    }
    if (current) result.push(current)
  }
  return result
})

function compareBlockNames(block: CompareBlock) {
  return [...new Set(block.mine.map(slot => slot.name).filter(Boolean))]
}

function compareBlockPartnerNames(block: CompareBlock) {
  return [...new Set(block.partner.map(slot => slot.name).filter(Boolean))]
}

function compareBlockName(block: CompareBlock) {
  const mine = compareBlockNames(block)
  const partner = compareBlockPartnerNames(block)
  return (mine.length ? mine : partner).join('、') || '课程'
}

function compareBlockPartnerName(block: CompareBlock) {
  const mine = compareBlockNames(block).join('、')
  const partner = compareBlockPartnerNames(block).join('、')
  return partner && partner !== mine ? partner : ''
}

function compareBlockClass(block: CompareBlock) {
  if (block.mine.length && block.partner.length) return 'schedule-compare-block--both'
  return block.mine.length ? 'schedule-compare-block--mine' : 'schedule-compare-block--partner'
}

function compareBlockStyle(block: CompareBlock) {
  return {
    gridColumn: String(block.day + 2),
    gridRow: `${block.start + 1} / span ${block.end - block.start + 1}`,
  }
}

function compareBlockTitle(block: CompareBlock) {
  const parts: string[] = []
  if (block.mine.length) {
    parts.push(`我：${[...new Set(block.mine.map(slot => `${slot.name}${slot.location ? ` · ${slot.location}` : ''}`))].join('、')}`)
  }
  if (block.partner.length) {
    parts.push(`TA：${[...new Set(block.partner.map(slot => `${slot.name}${slot.location ? ` · ${slot.location}` : ''}`))].join('、')}`)
  }
  return parts.join(' / ')
}

function cellClass(kind: CellKind) {
  return `schedule-cell--${kind}`
}

function courseClass(side: CourseSide) {
  return `schedule-course--${side}`
}

function weekText(slot: ScheduleSlot) {
  if (!slot.weeks.length) return '周次未记录'
  if (props.week === null) return `${formatWeeks(slot.weeks)} 周`
  return `第 ${props.week} 周`
}

function lessonRange(start: number, end: number) {
  return start === end ? `第 ${start} 节` : `第 ${start}–${end} 节`
}

// ---------- 拖动课程卡片：换星期/节次，拖底部调整节数 ----------
type DragKind = 'move' | 'resize'
interface DragTarget { weekday: number; start: number; end: number }
interface DragState {
  kind: DragKind
  index: number
  pointerId: number
  startX: number
  startY: number
  grabOffset: number
  span: number
  active: boolean
  target: DragTarget | null
  name: string
}

const drag = ref<DragState | null>(null)
let suppressClickUntil = 0

/** 用命中测试定位指针下的格子：卡片浮在网格上方，取坐标下第一个 cell。 */
function cellAt(x: number, y: number) {
  for (const element of document.elementsFromPoint(x, y)) {
    if (!(element instanceof Element)) continue
    const cell = element.closest<HTMLElement>('.schedule-cell')
    if (!cell) continue
    const day = Number(cell.dataset.day)
    const lesson = Number(cell.dataset.lesson)
    if (Number.isInteger(day) && Number.isInteger(lesson) && lesson >= 1) return { day, lesson }
  }
  return null
}

function detachDragListeners() {
  window.removeEventListener('pointermove', onDragMove)
  window.removeEventListener('pointerup', onDragEnd)
  window.removeEventListener('pointercancel', onDragCancel)
}

function beginCourseDrag(event: PointerEvent, course: CourseBlock, kind: DragKind) {
  if (!props.editable || props.slotMoving || props.addingLesson || course.side !== 'single') return
  // 触屏拖拽会与横向滚动冲突，暂只支持鼠标/触控笔，触屏保留点击编辑。
  if (event.button !== 0 || event.pointerType === 'touch') return
  const slot = course.slot
  const span = slot.lesson_end - slot.lesson_start + 1
  const cell = kind === 'move' ? cellAt(event.clientX, event.clientY) : null
  drag.value = {
    kind,
    index: course.index,
    pointerId: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
    grabOffset: cell ? Math.min(Math.max(cell.lesson - slot.lesson_start, 0), span - 1) : 0,
    span,
    active: false,
    target: null,
    name: slot.name,
  }
  window.addEventListener('pointermove', onDragMove)
  window.addEventListener('pointerup', onDragEnd)
  window.addEventListener('pointercancel', onDragCancel)
}

function onDragMove(event: PointerEvent) {
  const state = drag.value
  if (!state || event.pointerId !== state.pointerId) return
  if (!state.active) {
    if (Math.hypot(event.clientX - state.startX, event.clientY - state.startY) < 5) return
    state.active = true
    document.body.classList.add('schedule-dragging')
  }
  const slot = props.slots[state.index]
  const cell = cellAt(event.clientX, event.clientY)
  if (!slot || !cell) return
  const maxLesson = lessonCount.value
  if (state.kind === 'move') {
    const start = Math.min(Math.max(cell.lesson - state.grabOffset, 1), Math.max(1, maxLesson - state.span + 1))
    state.target = { weekday: cell.day, start, end: Math.min(maxLesson, start + state.span - 1) }
  } else {
    state.target = {
      weekday: slot.weekday,
      start: slot.lesson_start,
      end: Math.min(Math.max(cell.lesson, slot.lesson_start), maxLesson),
    }
  }
}

function endCourseDrag(event: PointerEvent, commit: boolean) {
  const state = drag.value
  detachDragListeners()
  document.body.classList.remove('schedule-dragging')
  drag.value = null
  if (!state || event.pointerId !== state.pointerId || !state.active) return
  // 拖动结束后浏览器仍会补发 click，短暂屏蔽以免误开编辑窗。
  suppressClickUntil = performance.now() + 400
  const slot = props.slots[state.index]
  const target = state.target
  if (!commit || !slot || !target) return
  if (target.weekday === slot.weekday && target.start === slot.lesson_start && target.end === slot.lesson_end) return
  emit('move', state.index, target.weekday, target.start, target.end)
}

function onDragEnd(event: PointerEvent) {
  endCourseDrag(event, true)
}

function onDragCancel(event: PointerEvent) {
  endCourseDrag(event, false)
}

function onCoursePointerDown(event: PointerEvent, course: CourseBlock) {
  beginCourseDrag(event, course, 'move')
}

function onResizePointerDown(event: PointerEvent, course: CourseBlock) {
  event.preventDefault()
  beginCourseDrag(event, course, 'resize')
}

function onCourseClick(course: CourseBlock) {
  if (!props.editable || performance.now() < suppressClickUntil) return
  emit('edit', course.index)
}

onBeforeUnmount(() => {
  detachDragListeners()
  document.body.classList.remove('schedule-dragging')
})

const draggingIndex = computed(() => (drag.value?.active ? drag.value.index : -1))
const dragTarget = computed(() => (drag.value?.active ? drag.value.target : null))

function isDropTarget(day: number, lesson: number) {
  const target = dragTarget.value
  return Boolean(target && target.weekday === day && lesson >= target.start && lesson <= target.end)
}

function ghostStyle(target: DragTarget) {
  return {
    gridColumn: String(target.weekday + 2),
    gridRow: `${target.start + 1} / span ${target.end - target.start + 1}`,
    width: 'calc(100% - 0.36rem)',
    marginLeft: '0.18rem',
  }
}

const ghost = computed(() => {
  const state = drag.value
  if (!state?.active || !state.target) return null
  return { name: state.name, target: state.target }
})

// ---------- 网格底部内嵌“添加一节” ----------
const nextPeriod = computed(() => (props.timing ? nextSchedulePeriod(props.timing) : null))
const addRowVisible = computed(() => {
  if (!props.editable || !props.timing) return false
  return props.timing.periods.length === lessonCount.value && props.timing.periods.length < MAX_LESSON
})
</script>

<template>
  <div class="schedule-board" :class="{ 'schedule-board--compact': compact, 'schedule-board--compare': comparing }">
    <div class="schedule-board__scroll">
      <div class="schedule-grid" :class="{ 'schedule-grid--add-row': addRowVisible }" :style="{ '--lesson-count': lessonCount }"
        @pointerleave="hoveredDay = null">
        <div class="schedule-corner" :style="{ gridColumn: '1', gridRow: '1' }">
          <span>节次 / 时间</span>
          <small v-if="dateLabels.length && week === null" class="schedule-corner__week">第 {{ displayWeek }} 周</small>
        </div>
        <div
          v-for="(day, index) in days"
          :key="day"
          class="schedule-day"
          :class="{ 'schedule-day--weekend': index > 4, 'schedule-day--active': activeDay === index, 'schedule-day--selectable': freeSelectable }"
          :style="{ gridColumn: String(index + 2), gridRow: '1' }"
          :role="freeSelectable ? 'button' : undefined"
          :tabindex="freeSelectable ? 0 : undefined"
          :aria-label="freeSelectable ? `选中${day}这一列` : undefined"
          :title="freeSelectable ? `选中${day}这一列，再点空闲格发出邀请` : dateTitle(index)"
          @click="selectDay(index)"
          @keydown.enter.prevent="selectDay(index)"
          @pointerenter="onDayEnter(index)"
        >
          <span>{{ day }}</span>
          <small>{{ index < 5 ? '工作日' : '周末' }}</small>
          <small v-if="dateLabels.length" class="schedule-day__date">{{ dateLabels[index] }}</small>
        </div>

        <div
          v-if="activeDay !== null"
          class="schedule-column-highlight"
          :style="{ gridColumn: String(activeDay + 2), gridRow: `1 / span ${lessonCount + 1}` }"
          aria-hidden="true"
        ></div>

        <div
          v-for="lesson in lessonCount"
          :key="`time-${lesson}`"
          class="schedule-time"
          :class="[segmentClassAt(lesson), { 'schedule-time--segment-start': segmentStartsAt(lesson) }]"
          :style="{ gridColumn: '1', gridRow: String(lesson + 1) }"
        >
          <span v-if="segmentLabelAt(lesson)" class="schedule-time__segment">{{ segmentLabelAt(lesson) }}</span>
          <strong>{{ String(lesson).padStart(2, '0') }}</strong>
          <span>第{{ lesson }}节</span>
          <small v-if="timing?.periods[lesson - 1]">{{ timing.periods[lesson - 1][0] }}–{{ timing.periods[lesson - 1][1] }}</small>
        </div>

        <component
          v-for="cell in cells"
          :is="cellComponent(cell)"
          :key="`${cell.day}-${cell.lesson}`"
          class="schedule-cell"
          :class="[cellClass(cell.kind), {
            'schedule-cell--segment-start': cell.segmentStart,
            'schedule-cell--drop-target': isDropTarget(cell.day, cell.lesson),
            'schedule-cell--free-selectable': freeSelectable && cell.kind === 'both-free',
            'schedule-cell--active-day': activeDay === cell.day,
            'schedule-cell--selected-free': isSelectedFree(cell.day, cell.lesson),
          }]"
          :style="{ gridColumn: String(cell.day + 2), gridRow: String(cell.lesson + 1) }"
          :data-day="cell.day"
          :data-lesson="cell.lesson"
          :type="cellComponent(cell) === 'button' ? 'button' : undefined"
          :aria-label="editable
            ? `${days[cell.day]}第${cell.lesson}节：添加课程或日程`
            : (freeSelectable && cell.kind === 'both-free' ? `${days[cell.day]}第${cell.lesson}节：双方空闲，点按邀请 TA` : undefined)"
          @click="onCellClick(cell, $event)"
          @pointerdown="onCellPointerDown(cell, $event)"
          @pointerenter="onCellPointerEnter(cell, $event)"
          @pointerleave="onCellPointerLeave(cell)"
        ><span v-if="editable" class="schedule-cell__add" aria-hidden="true">＋</span></component>

        <template v-if="compareMode">
          <article
            v-for="block in compareBlocks"
            :key="`compare-${block.key}-${block.start}`"
            class="schedule-compare-block"
            :class="compareBlockClass(block)"
            :style="compareBlockStyle(block)"
            :title="compareBlockTitle(block)"
          >
            <span class="schedule-compare-block__name">{{ compareBlockName(block) }}</span>
            <span v-if="compareBlockPartnerName(block)" class="schedule-compare-block__partner">TA · {{ compareBlockPartnerName(block) }}</span>
            <span v-if="block.sameRoom" class="schedule-compare-block__same" title="同教室同时间" aria-label="同教室同时间"></span>
          </article>
        </template>

        <template v-else>
          <component
            v-for="course in courseBlocks"
            :is="editable ? 'button' : 'article'"
            :key="course.key"
            class="schedule-course"
            :class="[courseClass(course.side), {
              'schedule-course--event': course.slot.kind === 'event',
              'schedule-course--draggable': editable && !slotMoving,
              'schedule-course--dragging': draggingIndex === course.index && course.side === 'single',
            }]"
            :style="blockStyle(course)"
            :type="editable ? 'button' : undefined"
            :aria-label="editable ? `编辑${course.slot.name}` : undefined"
            :title="`${course.slot.name} · ${course.slot.location || '未填写地点'} · ${weekText(course.slot)}`"
            @click="onCourseClick(course)"
            @pointerdown="editable && onCoursePointerDown($event, course)"
          >
            <span class="schedule-course__name">{{ course.slot.kind === 'event' ? '◷ ' : '' }}{{ course.slot.name }}</span>
            <span class="schedule-course__location">{{ course.slot.kind === 'event' && !editable ? '个人日程' : course.slot.location || '未填写地点' }}</span>
            <span class="schedule-course__week">{{ weekText(course.slot) }}</span>
            <span
              v-if="editable && course.side === 'single'"
              class="schedule-course__resize"
              aria-hidden="true"
              title="拖动调整结束节次"
              @click.stop
              @pointerdown.stop="onResizePointerDown($event, course)"
            ></span>
          </component>
        </template>

        <button
          v-for="invitationBlock in invitationBlocks"
          :key="`invitation-${invitationBlock.invitation.id}`"
          type="button"
          class="schedule-invitation"
          :style="invitationBlock.style"
          :title="`${invitationBlock.invitation.title} · ${invitationHint(invitationBlock.invitation)}`"
          @click.stop="emit('invitation', invitationBlock.invitation.id)"
        >
          <span class="schedule-invitation__badge">邀请</span>
          <span class="schedule-invitation__name">{{ invitationBlock.invitation.title }}</span>
          <span class="schedule-invitation__hint">{{ invitationHint(invitationBlock.invitation) }}</span>
        </button>

        <div
          v-if="ghost"
          class="schedule-course schedule-course--ghost"
          :style="ghostStyle(ghost.target)"
          aria-hidden="true"
        >
          <span class="schedule-course__name">{{ ghost.name }}</span>
          <span class="schedule-course__location">{{ days[ghost.target.weekday] }} {{ lessonRange(ghost.target.start, ghost.target.end) }}</span>
        </div>

        <template v-if="addRowVisible">
          <div
            class="schedule-time schedule-add-row__time"
            :style="{ gridColumn: '1', gridRow: String(lessonCount + 2) }"
          >
            <strong>{{ String(lessonCount + 1).padStart(2, '0') }}</strong>
            <span>第{{ lessonCount + 1 }}节</span>
            <small v-if="nextPeriod">{{ nextPeriod[0] }}–{{ nextPeriod[1] }}</small>
          </div>
          <button
            type="button"
            class="schedule-add-row"
            :style="{ gridColumn: `2 / span ${days.length}`, gridRow: String(lessonCount + 2) }"
            :disabled="!nextPeriod || addingLesson"
            :title="nextPeriod ? `添加第 ${lessonCount + 1} 节 ${nextPeriod[0]}–${nextPeriod[1]}` : '当天剩余时间不足，无法再加一节'"
            @click="emit('addLesson')"
          >
            <template v-if="addingLesson">保存中…</template>
            <template v-else-if="nextPeriod">＋ 添加一节 <small>{{ nextPeriod[0] }}–{{ nextPeriod[1] }}</small></template>
            <template v-else>当天剩余时间不足，无法再加一节</template>
          </button>
        </template>
      </div>
    </div>

    <div v-if="!courseBlocks.length" class="schedule-board__empty">
      <span class="text-2xl">🌿</span>
      <span>{{ editable ? '点击空白格，开始添加课程或日程。' : '所选周次没有记录课程或日程。' }}</span>
    </div>
  </div>
</template>

<style scoped>
.schedule-board {
  overflow: hidden;
  border: 1px solid rgba(107, 92, 231, 0.12);
  border-radius: 1rem;
  background: rgba(255, 255, 255, 0.42);
}

.schedule-board__scroll {
  overflow-x: auto;
  padding: 0.65rem;
}

.schedule-grid {
  display: grid;
  min-width: 760px;
  grid-template-columns: 5rem repeat(7, minmax(6.9rem, 1fr));
  grid-template-rows: 3.3rem repeat(var(--lesson-count), minmax(3.9rem, auto));
  gap: 0.35rem;
}

.schedule-grid--add-row {
  grid-template-rows: 3.3rem repeat(var(--lesson-count), minmax(3.9rem, auto)) auto;
}

.schedule-corner,
.schedule-day,
.schedule-time,
.schedule-cell,
.schedule-course {
  min-width: 0;
}

.schedule-corner {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #a5a0c2;
  font-size: 0.64rem;
}

.schedule-corner__week {
  margin-top: 0.15rem;
  color: #7569bd;
  font-size: 0.56rem;
  font-weight: 600;
}

.schedule-day {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border-radius: 0.85rem;
  background: rgba(244, 243, 251, 0.88);
  color: #493db0;
  font-size: 0.78rem;
  font-weight: 700;
}

.schedule-day small {
  margin-top: 0.15rem;
  color: #a5a0c2;
  font-size: 0.58rem;
  font-weight: 500;
}

.schedule-day .schedule-day__date {
  margin-top: 0.05rem;
  color: #7569bd;
  font-weight: 700;
}

.schedule-day--weekend {
  color: #9e6791;
  background: rgba(240, 166, 200, 0.13);
}

.schedule-day--selectable {
  cursor: pointer;
  transition: box-shadow 0.18s ease, transform 0.18s ease;
}

.schedule-day--selectable:hover,
.schedule-day--active {
  box-shadow: inset 0 0 0 2px #22c55e;
  transform: translateY(-1px);
}

.schedule-day--active {
  color: #15803d;
}

.schedule-column-highlight {
  position: relative;
  z-index: 8;
  border: 2px solid #22c55e;
  border-radius: 0.9rem;
  background: rgba(34, 197, 94, 0.055);
  box-shadow: 0 14px 32px rgba(22, 163, 74, 0.2), inset 0 0 0 1px rgba(255, 255, 255, 0.55);
  pointer-events: none;
  transform: translateY(-4px);
  animation: schedule-column-lift 0.2s cubic-bezier(0.22, 1, 0.36, 1);
}

@keyframes schedule-column-lift {
  from { opacity: 0; transform: translateY(0) scale(0.99); }
  to { opacity: 1; transform: translateY(-4px) scale(1); }
}

.schedule-time {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding-right: 0.35rem;
  text-align: right;
}

.schedule-time--segment-start,
.schedule-cell--segment-start {
  border-top: 2px solid rgba(107, 92, 231, 0.2);
}

.schedule-time__segment {
  display: inline-block;
  align-self: flex-end;
  margin-bottom: 0.25rem;
  border-radius: 999px;
  padding: 0.12rem 0.3rem;
  background: #eef2ff;
  color: #4f46e5;
  font-size: 0.56rem;
  font-weight: 700;
  line-height: 1;
}

.schedule-time--noon .schedule-time__segment { background: #fff7ed; color: #c2410c; }
.schedule-time--afternoon .schedule-time__segment { background: #ecfdf5; color: #047857; }
.schedule-time--evening .schedule-time__segment { background: #f3e8ff; color: #7e22ce; }

.schedule-time strong {
  color: #6e698c;
  font-size: 0.72rem;
  line-height: 1;
}

.schedule-time span {
  margin-top: 0.28rem;
  color: #a5a0c2;
  font-size: 0.56rem;
  white-space: nowrap;
}

.schedule-time small {
  margin-top: 0.16rem;
  color: #706b8b;
  font-size: 0.53rem;
  line-height: 1.15;
  white-space: nowrap;
}

.schedule-cell {
  border: 1px solid rgba(107, 92, 231, 0.07);
  border-radius: 0.65rem;
  background: rgba(255, 255, 255, 0.56);
}

button.schedule-cell:hover { background: #eae8fa; border-color: #9787ea; }
.schedule-cell__add { color: #6b5ce7; opacity: 0; font-size: 1rem; transition: opacity 0.16s ease; }
button.schedule-cell:hover .schedule-cell__add,
button.schedule-cell:focus-visible .schedule-cell__add { opacity: 0.55; }
button.schedule-cell:focus-visible, button.schedule-course:focus-visible { outline: 2px solid #493db0; outline-offset: 2px; }
button.schedule-cell--free-selectable { cursor: pointer; touch-action: none; user-select: none; }
button.schedule-cell--free-selectable:hover {
  background: rgba(74, 222, 128, 0.28);
  border-color: #22c55e;
  box-shadow: inset 0 0 0 1px rgba(34, 197, 94, 0.45);
}
.schedule-cell--selected-free {
  z-index: 1;
  background: rgba(34, 197, 94, 0.28) !important;
  border-color: #16a34a !important;
  box-shadow: inset 0 0 0 2px rgba(22, 163, 74, 0.8);
}
.schedule-cell--active-day { border-color: rgba(34, 197, 94, 0.2); }
.schedule-cell--different-weeks { background: repeating-linear-gradient(135deg, #f4f3fb 0 6px, #eae8fa 6px 12px); }

.schedule-cell--both-free {
  border-color: rgba(16, 185, 129, 0.13);
  background: rgba(167, 243, 208, 0.2);
}

.schedule-cell--one-busy {
  border-color: rgba(107, 92, 231, 0.1);
  background: rgba(234, 232, 250, 0.6);
}

.schedule-cell--both-busy {
  border-color: rgba(240, 166, 200, 0.15);
  background: rgba(240, 166, 200, 0.18);
}

.schedule-cell--same-room {
  border-color: rgba(245, 158, 11, 0.22);
  background: rgba(253, 230, 138, 0.34);
}

.schedule-cell--drop-target {
  border-color: rgba(107, 92, 231, 0.55);
  background: rgba(107, 92, 231, 0.14);
}

.schedule-course {
  position: relative;
  z-index: 2;
  display: flex;
  min-height: 0;
  flex-direction: column;
  align-items: flex-start;
  justify-self: start;
  text-align: left;
  align-self: stretch;
  overflow: hidden;
  margin: 0.18rem;
  border: 1px solid rgba(107, 92, 231, 0.22);
  border-radius: 0.65rem;
  padding: 0.48rem 0.55rem;
  box-shadow: 0 5px 12px rgba(31, 27, 51, 0.05);
  user-select: none;
  -webkit-user-select: none;
}

.schedule-invitation {
  position: relative;
  z-index: 5;
  display: flex;
  min-width: 0;
  flex-direction: column;
  align-items: flex-start;
  align-self: stretch;
  justify-self: start;
  overflow: hidden;
  margin: 0.18rem;
  border: 1.5px dashed rgba(190, 139, 34, 0.65);
  border-radius: 0.65rem;
  padding: 0.42rem 0.5rem;
  background: rgba(255, 248, 226, 0.96);
  color: #75520d;
  text-align: left;
  box-shadow: 0 5px 14px rgba(127, 92, 18, 0.1);
}

.schedule-invitation:hover {
  background: #fffdf5;
  border-color: #b8861c;
}

.schedule-invitation__badge {
  font-size: 0.52rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  color: #a06a0a;
}

.schedule-invitation__name {
  margin-top: 0.1rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.66rem;
  font-weight: 700;
}

.schedule-invitation__hint {
  margin-top: 0.08rem;
  font-size: 0.55rem;
  color: #9a7a36;
}

.schedule-course--draggable {
  cursor: grab;
}

.schedule-course--dragging {
  opacity: 0.3;
}

.schedule-course--ghost {
  z-index: 4;
  border: 2px dashed rgba(73, 61, 176, 0.7);
  background: rgba(107, 92, 231, 0.16);
  color: #493db0;
  pointer-events: none;
  box-shadow: none;
}

.schedule-course--ghost .schedule-course__location {
  color: #493db0;
  opacity: 0.8;
}

.schedule-course__resize {
  position: absolute;
  bottom: 0.1rem;
  left: 50%;
  width: 2rem;
  height: 0.6rem;
  transform: translateX(-50%);
  cursor: ns-resize;
  touch-action: none;
}

.schedule-course__resize::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 1.4rem;
  height: 3px;
  transform: translate(-50%, -50%);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.55);
}

.schedule-course--event .schedule-course__resize::after {
  background: rgba(255, 255, 255, 0.45);
}

:global(body.schedule-dragging) {
  cursor: grabbing;
}

:global(body.schedule-dragging *) {
  cursor: grabbing !important;
  user-select: none;
}

.schedule-add-row {
  display: flex;
  min-height: 2.6rem;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  border: 1px dashed rgba(107, 92, 231, 0.45);
  border-radius: 0.65rem;
  background: rgba(107, 92, 231, 0.05);
  color: #493db0;
  font-size: 0.72rem;
  font-weight: 600;
  transition: background 0.16s ease, border-color 0.16s ease;
}

.schedule-add-row small {
  color: #706b8b;
  font-size: 0.62rem;
  font-weight: 500;
}

.schedule-add-row:hover:not(:disabled) {
  border-color: #6b5ce7;
  background: rgba(107, 92, 231, 0.12);
}

.schedule-add-row:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}

.schedule-add-row:focus-visible {
  outline: 2px solid #493db0;
  outline-offset: 2px;
}

.schedule-course--single,
.schedule-course--mine {
  background: linear-gradient(145deg, rgba(107, 92, 231, 0.93), rgba(139, 124, 240, 0.86));
  color: white;
}

.schedule-course--partner {
  border-color: rgba(240, 166, 200, 0.44);
  background: linear-gradient(145deg, rgba(240, 166, 200, 0.92), rgba(251, 191, 211, 0.86));
  color: #6e3155;
}

.schedule-course--event { border: 2px dashed currentColor; }
.schedule-course--single.schedule-course--event { background: #0f766e; color: white; }

.schedule-course__name {
  display: -webkit-box;
  overflow: hidden;
  width: 100%;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  font-size: 0.68rem;
  font-weight: 700;
  line-height: 1.35;
}

.schedule-course__location,
.schedule-course__week {
  display: block;
  overflow: hidden;
  width: 100%;
  margin-top: 0.23rem;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.58rem;
  opacity: 0.82;
}

.schedule-course__week {
  margin-top: auto;
  opacity: 0.68;
}

.schedule-board__empty {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  border-top: 1px solid rgba(107, 92, 231, 0.08);
  padding: 1.4rem 1rem;
  color: #6e698c;
  font-size: 0.78rem;
}

.schedule-board--compact .schedule-grid {
  grid-template-rows: 2.8rem repeat(var(--lesson-count), minmax(3.2rem, auto));
}

.schedule-board--compact .schedule-grid--add-row {
  grid-template-rows: 2.8rem repeat(var(--lesson-count), minmax(3.2rem, auto)) auto;
}

/* 对比模式：把两张高饱和课程卡压成低饱和的“共享格子 + 双侧色条” */
.schedule-board--compare .schedule-cell {
  border-color: transparent;
  border-radius: 0.52rem;
  background: rgba(255, 255, 255, 0.72);
}

.schedule-board--compare .schedule-cell--both-free {
  border-color: transparent;
  background: #f1faf4;
}

.schedule-board--compare .schedule-cell--one-busy {
  border-color: transparent;
  background: rgba(107, 92, 231, 0.045);
}

.schedule-board--compare .schedule-cell--both-busy {
  border-color: transparent;
  background: rgba(240, 166, 200, 0.08);
}

.schedule-board--compare .schedule-cell--different-weeks {
  border-color: transparent;
  background: repeating-linear-gradient(135deg, #faf9fe 0 8px, #f1effa 8px 16px);
}

.schedule-board--compare .schedule-cell--same-room {
  position: relative;
  border-color: transparent;
  background: rgba(245, 158, 11, 0.065);
}

.schedule-board--compare .schedule-cell--same-room::after {
  content: '';
  position: absolute;
  top: 0.32rem;
  right: 0.32rem;
  width: 0.32rem;
  height: 0.32rem;
  border-radius: 999px;
  background: #e7a91b;
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.7);
  pointer-events: none;
}

.schedule-board--compare .schedule-course {
  padding: 0.34rem 0.4rem;
  border-radius: 0.45rem;
  box-shadow: none;
}

.schedule-board--compare .schedule-course--mine {
  border: 1px solid rgba(107, 92, 231, 0.16);
  border-left: 3px solid #6b5ce7;
  background: rgba(107, 92, 231, 0.14);
  color: #4136a0;
}

.schedule-board--compare .schedule-course--partner {
  border: 1px solid rgba(240, 166, 200, 0.24);
  border-right: 3px solid #e88ab8;
  background: rgba(240, 166, 200, 0.2);
  color: #6f3454;
}

.schedule-board--compare .schedule-course--event {
  border-style: dashed;
}

.schedule-board--compare .schedule-course__name {
  font-size: 0.64rem;
  line-height: 1.2;
  -webkit-line-clamp: 2;
}

.schedule-board--compare .schedule-course__location,
.schedule-board--compare .schedule-course__week {
  display: none;
}

.schedule-board--compare .schedule-day {
  background: rgba(248, 247, 252, 0.9);
}

.schedule-board--compare .schedule-column-highlight {
  border-width: 1.5px;
  background: rgba(34, 197, 94, 0.035);
  box-shadow: 0 12px 26px rgba(22, 163, 74, 0.13), inset 0 0 0 1px rgba(255, 255, 255, 0.6);
}

/* 对比模式：把两侧课程合并成一块，左右色条表示人 */
.schedule-compare-block {
  position: relative;
  z-index: 2;
  display: flex;
  min-width: 0;
  min-height: 0;
  flex-direction: column;
  align-items: flex-start;
  align-self: stretch;
  justify-self: stretch;
  overflow: hidden;
  margin: 0.18rem;
  border-radius: 0.48rem;
  padding: 0.34rem 0.42rem;
  text-align: left;
  gap: 0.1rem;
}

.schedule-compare-block--mine {
  border: 1px solid rgba(107, 92, 231, 0.18);
  border-left: 3px solid #6b5ce7;
  background: #f2effd;
}

.schedule-compare-block--partner {
  border: 1px solid rgba(240, 166, 200, 0.3);
  border-right: 3px solid #e88ab8;
  background: #fdf1f7;
}

.schedule-compare-block--both {
  border: 1px solid rgba(107, 92, 231, 0.14);
  border-left: 3px solid #6b5ce7;
  border-right: 3px solid #e88ab8;
  background: linear-gradient(90deg, #f2effd, #f7effa 48%, #fdf1f7);
}

.schedule-compare-block__name {
  display: -webkit-box;
  overflow: hidden;
  width: 100%;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  color: #3f3498;
  font-size: 0.65rem;
  font-weight: 700;
  line-height: 1.22;
}

.schedule-compare-block--partner .schedule-compare-block__name {
  color: #6f3454;
}

.schedule-compare-block--both .schedule-compare-block__name {
  color: #413866;
}

.schedule-compare-block__partner {
  overflow: hidden;
  width: 100%;
  color: #9a5678;
  font-size: 0.56rem;
  line-height: 1.2;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.schedule-compare-block__same {
  position: absolute;
  top: 0.34rem;
  right: 0.4rem;
  width: 0.34rem;
  height: 0.34rem;
  border-radius: 999px;
  background: #e7a91b;
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.8);
}
</style>
