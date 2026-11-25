import type { ScheduleSegments, ScheduleSlot } from '@/types'
import type { ScheduleTiming } from '@/types'

export const DAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
export const MAX_WEEK = 53
export const MIN_LESSON = 1
export const MAX_LESSON = 24
export const DEFAULT_LESSON_COUNT = 12

export type SchedulePeriodSegment = 'morning' | 'noon' | 'afternoon' | 'evening'

const DEFAULT_SEGMENTS: ScheduleSegments = { noon: '12:00', afternoon: '14:00', evening: '18:00' }

const PERIOD_SEGMENT_LABELS: Record<SchedulePeriodSegment, string> = {
  morning: '上午',
  noon: '中午',
  afternoon: '下午',
  evening: '晚上',
}

function clockMinutes(value: string) {
  const [hour, minute] = value.split(':').map(Number)
  return hour * 60 + minute
}

function clockValue(value: number) {
  return `${String(Math.floor(value / 60)).padStart(2, '0')}:${String(value % 60).padStart(2, '0')}`
}

/**
 * 在现有作息末尾追加一节时使用的默认时间。
 * 与作息窗格“添加一节”保持同一规则：上一节结束后再留默认节间隔；
 * 当天剩余时间不足、已达 24 节上限或作息为空时返回 null。
 */
export function nextSchedulePeriod(timing: ScheduleTiming): [string, string] | null {
  if (timing.periods.length >= MAX_LESSON) return null
  const last = timing.periods[timing.periods.length - 1]
  if (!last) return null
  const start = clockMinutes(last[1]) + timing.break_minutes
  if (start + timing.lesson_minutes >= 24 * 60) return null
  return [clockValue(start), clockValue(start + timing.lesson_minutes)]
}

/** 返回追加一节后的新作息；不能追加时返回 null（不修改入参）。 */
export function appendSchedulePeriod(timing: ScheduleTiming): ScheduleTiming | null {
  const period = nextSchedulePeriod(timing)
  if (!period) return null
  return {
    ...timing,
    first_start: timing.periods[0]?.[0] ?? timing.first_start,
    periods: [...timing.periods, period],
  }
}

export function periodSegment(timing: ScheduleTiming | null | undefined, index: number): SchedulePeriodSegment {
  const period = timing?.periods[index]
  const segments = timing?.segments ?? DEFAULT_SEGMENTS
  const start = clockMinutes(period?.[0] || '08:00')
  if (start >= clockMinutes(segments.evening)) return 'evening'
  if (start >= clockMinutes(segments.afternoon)) return 'afternoon'
  if (start >= clockMinutes(segments.noon)) return 'noon'
  return 'morning'
}

export function periodSegmentLabel(segment: SchedulePeriodSegment) {
  return PERIOD_SEGMENT_LABELS[segment]
}

export function defaultScheduleSegments(): ScheduleSegments {
  return { ...DEFAULT_SEGMENTS }
}

export function normalizeScheduleSegments(value?: Partial<ScheduleSegments> | null): ScheduleSegments {
  const fallback = defaultScheduleSegments()
  const valid = /^([01]\d|2[0-3]):[0-5]\d$/
  const next = {
    noon: typeof value?.noon === 'string' && valid.test(value.noon) ? value.noon : fallback.noon,
    afternoon: typeof value?.afternoon === 'string' && valid.test(value.afternoon) ? value.afternoon : fallback.afternoon,
    evening: typeof value?.evening === 'string' && valid.test(value.evening) ? value.evening : fallback.evening,
  }
  if (clockMinutes(next.noon) >= clockMinutes(next.afternoon) || clockMinutes(next.afternoon) >= clockMinutes(next.evening)) {
    return fallback
  }
  return next
}

export function defaultScheduleTiming(count = DEFAULT_LESSON_COUNT): ScheduleTiming {
  const firstStart = 8 * 60
  const lessonMinutes = 45
  const breakMinutes = 10
  const clock = (value: number) => `${String(Math.floor(value / 60)).padStart(2, '0')}:${String(value % 60).padStart(2, '0')}`
  const periods = Array.from({ length: count }, (_, index) => {
    const start = firstStart + index * (lessonMinutes + breakMinutes)
    return [clock(start), clock(start + lessonMinutes)] as [string, string]
  })
  return {
    term_start: null,
    first_start: '08:00',
    lesson_minutes: lessonMinutes,
    break_minutes: breakMinutes,
    segments: defaultScheduleSegments(),
    periods,
  }
}

export function normalizeScheduleTiming(value?: Partial<ScheduleTiming> | null): ScheduleTiming {
  const fallback = defaultScheduleTiming()
  if (!value) return fallback
  const periods = Array.isArray(value.periods) && value.periods.length >= MIN_LESSON && value.periods.length <= MAX_LESSON
    ? value.periods.map((period, index) => [period?.[0] || fallback.periods[index][0], period?.[1] || fallback.periods[index][1]] as [string, string])
    : fallback.periods
  return {
    term_start: value.term_start ?? fallback.term_start,
    first_start: value.first_start || periods[0][0],
    lesson_minutes: value.lesson_minutes ?? fallback.lesson_minutes,
    break_minutes: value.break_minutes ?? fallback.break_minutes,
    segments: normalizeScheduleSegments(value.segments),
    periods,
  }
}

export function lessonTime(timing: ScheduleTiming, lesson: number): string {
  const period = timing.periods[lesson - 1]
  return period ? `${period[0]}–${period[1]}` : ''
}

export function scheduleWeeks(slots: ScheduleSlot[]) {
  const recorded = slots.flatMap(slot => slot.weeks)
  const last = recorded.length ? Math.max(...recorded) : 16
  return Array.from({ length: Math.min(MAX_WEEK, last) }, (_, i) => i + 1)
}

export function parseWeekSelection(text: string): number[] {
  const weeks = new Set<number>()
  for (const part of text.trim().replace(/，/g, ',').split(',')) {
    const match = part.trim().match(/^(\d{1,2})(?:\s*-\s*(\d{1,2}))?$/)
    if (!match) throw new Error('周次请填写如 1-16 或 1,3,5，单次日程只填一周')
    const start = Number(match[1])
    const end = Number(match[2] ?? match[1])
    if (start < 1 || end > MAX_WEEK || end < start) throw new Error('周次范围应在 1–53 之间，结束周不能早于开始周')
    for (let week = start; week <= end; week++) weeks.add(week)
  }
  return [...weeks].sort((a, b) => a - b)
}

export function formatWeeks(weeks: number[]): string {
  if (!weeks.length) return '周次未记录'
  const values = [...new Set(weeks)].sort((a, b) => a - b)
  const ranges: string[] = []
  let start = values[0]
  let end = start
  for (const week of values.slice(1)) {
    if (week === end + 1) { end = week; continue }
    ranges.push(start === end ? `${start}` : `${start}-${end}`)
    start = end = week
  }
  ranges.push(start === end ? `${start}` : `${start}-${end}`)
  return ranges.join(',')
}
