<script setup lang="ts">
import { computed } from 'vue'
import UserAvatar from '@/components/UserAvatar.vue'
import type { ScheduleCompareResult, ScheduleRecord, ScheduleSlot } from '@/types'

const props = defineProps<{
  mySchedule: ScheduleRecord | null
  partner: ScheduleRecord | null
  result: ScheduleCompareResult | null
}>()

const emit = defineEmits<{ back: [] }>()

const days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
const maxLesson = 12

const mySlots = computed<ScheduleSlot[]>(() => props.mySchedule?.slots ?? [])
const partnerSlots = computed<ScheduleSlot[]>(() => props.partner?.slots ?? [])

type CellKind = 'both-busy' | 'one-busy' | 'both-free' | 'same-room'

function slotCovers(s: ScheduleSlot, weekday: number, lesson: number) {
  return s.weekday === weekday && lesson >= s.lesson_start && lesson <= s.lesson_end
}

function cellKind(day: number, lesson: number): CellKind {
  const mine = mySlots.value.some((s) => slotCovers(s, day, lesson))
  const theirs = partnerSlots.value.some((s) => slotCovers(s, day, lesson))
  if (mine && theirs) {
    const sameRoom = props.result?.same_classroom.some(
      (c) => c.weekday === day && slotCovers(c.a, day, lesson),
    )
    return sameRoom ? 'same-room' : 'both-busy'
  }
  if (mine || theirs) return 'one-busy'
  return 'both-free'
}

const grid = computed(() => {
  const rows: { day: number; lessons: CellKind[] }[] = []
  for (let d = 0; d < 7; d++) {
    const lessons: CellKind[] = []
    for (let l = 1; l <= maxLesson; l++) lessons.push(cellKind(d, l))
    rows.push({ day: d, lessons })
  }
  return rows
})

const freeSlots = computed(() => {
  if (props.result) {
    return props.result.both_free.map((f) => ({
      day: days[f.weekday],
      slots: f.lesson_start === f.lesson_end
        ? `第 ${f.lesson_start} 节`
        : `第 ${f.lesson_start}-${f.lesson_end} 节`,
    }))
  }
  return []
})

const sameRoomList = computed(() =>
  (props.result?.same_classroom ?? []).map((c) => ({
    day: days[c.weekday],
    name: c.a.name,
    location: c.a.location,
    range: `${c.a.lesson_start}-${c.a.lesson_end} 节`,
  })),
)

const overlapList = computed(() =>
  (props.result?.overlaps ?? []).map((c) => ({
    day: days[c.weekday],
    mine: c.a.name,
    theirs: c.b.name,
    range: `${Math.max(c.a.lesson_start, c.b.lesson_start)}-${Math.min(c.a.lesson_end, c.b.lesson_end)} 节`,
  })),
)

const cellStyle: Record<CellKind, string> = {
  'both-busy': 'bg-blush/30 text-blush',
  'one-busy': 'bg-primary-100 text-primary-400',
  'both-free': 'bg-emerald-100 text-emerald-600',
  'same-room': 'bg-amber-100 text-amber-600',
}
</script>

<template>
  <div class="mt-8">
    <div class="glass-card p-8">
      <!-- 对比双方 -->
      <div class="flex flex-wrap items-center gap-4">
        <div class="flex items-center gap-2">
          <UserAvatar :name="'我'" :size="32" />
          <span class="text-sm text-ink font-medium">我</span>
        </div>
        <span class="text-faint">vs</span>
        <div class="flex items-center gap-2">
          <UserAvatar :name="partner?.owner?.display_name ?? ''" :size="32" />
          <span class="text-sm text-ink font-medium">{{ partner?.owner?.display_name }}</span>
        </div>
        <div class="ml-auto">
          <button class="btn-ghost !px-4 !py-1.5 text-xs" @click="emit('back')">重新选择</button>
        </div>
      </div>

      <!-- 图例 -->
      <div class="mt-6 flex flex-wrap gap-4 text-xs text-sub">
        <span class="flex items-center gap-1.5"><span class="w-3.5 h-3.5 rounded bg-emerald-100 border border-emerald-300"></span>双方都空闲（适合约）</span>
        <span class="flex items-center gap-1.5"><span class="w-3.5 h-3.5 rounded bg-primary-100 border border-primary-300"></span>有一方有课</span>
        <span class="flex items-center gap-1.5"><span class="w-3.5 h-3.5 rounded bg-amber-100 border border-amber-300"></span>同教室同时间（意外相遇！）</span>
        <span class="flex items-center gap-1.5"><span class="w-3.5 h-3.5 rounded bg-blush/20 border border-blush/40"></span>双方都有课</span>
      </div>

      <!-- 周课表网格 -->
      <div class="mt-6 overflow-x-auto">
        <div class="min-w-[640px]">
          <div class="grid grid-cols-[48px_repeat(7,1fr)] gap-1">
            <div></div>
            <div v-for="d in days" :key="d" class="text-center text-xs font-medium text-sub py-2">{{ d }}</div>
          </div>
          <div v-for="lesson in maxLesson" :key="lesson" class="grid grid-cols-[48px_repeat(7,1fr)] gap-1 mt-1">
            <div class="text-right pr-2 text-[10px] text-faint leading-7">{{ lesson }}</div>
            <div
              v-for="d in 7"
              :key="d"
              class="h-7 rounded-md text-[10px] flex items-center justify-center font-medium transition"
              :class="cellStyle[grid[d - 1].lessons[lesson - 1]]"
            >
              {{ grid[d - 1].lessons[lesson - 1] === 'both-free' ? '·' : '' }}
            </div>
          </div>
        </div>
      </div>

      <!-- 推荐空闲时段 -->
      <div class="mt-8">
        <h3 class="text-sm font-semibold text-ink mb-3">推荐空闲时段</h3>
        <div v-if="freeSlots.length" class="space-y-2">
          <div v-for="f in freeSlots" :key="f.day" class="flex items-center gap-3 text-sm bg-emerald-50 rounded-lg px-4 py-2.5">
            <span class="text-emerald-700 font-medium w-12">{{ f.day }}</span>
            <span class="text-emerald-700">{{ f.slots }}</span>
          </div>
        </div>
        <p v-else class="text-sm text-faint">本学期你们似乎没有共同空闲时段，换个学期再约吧～</p>
        <p class="mt-4 text-xs text-faint">以上时段双方都无课（按整学期安全空闲计算），快约起来吧～</p>
      </div>

      <!-- 同教室 -->
      <div v-if="sameRoomList.length" class="mt-8">
        <h3 class="text-sm font-semibold text-ink mb-3">同教室时段（意外相遇！）</h3>
        <div class="space-y-2">
          <div v-for="(r, i) in sameRoomList" :key="i" class="flex items-center gap-3 text-sm bg-amber-50 rounded-lg px-4 py-2.5">
            <span class="text-amber-700 font-medium w-12">{{ r.day }}</span>
            <span class="text-amber-700 flex-1">{{ r.name }} · {{ r.location }}</span>
            <span class="text-amber-600 text-xs">{{ r.range }}</span>
          </div>
        </div>
      </div>

      <!-- 冲突 -->
      <div v-if="overlapList.length" class="mt-8">
        <h3 class="text-sm font-semibold text-ink mb-3">时间冲突</h3>
        <div class="space-y-2">
          <div v-for="(r, i) in overlapList" :key="i" class="flex items-center gap-3 text-sm bg-red-50 rounded-lg px-4 py-2.5">
            <span class="text-red-700 font-medium w-12">{{ r.day }}</span>
            <span class="text-red-700 flex-1">{{ r.mine }} vs {{ r.theirs }}</span>
            <span class="text-red-600 text-xs">{{ r.range }}</span>
          </div>
        </div>
        <p class="mt-3 text-xs text-faint">冲突已按周次交集计算，只有真正同时上课才算。</p>
      </div>
    </div>
  </div>
</template>
