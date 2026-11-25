<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import ScheduleWeekGrid from '@/components/schedule/ScheduleWeekGrid.vue'
import ScheduleWeekPicker from '@/components/schedule/ScheduleWeekPicker.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import type { ScheduleRecord } from '@/types'
import { scheduleWeeks } from './calendar'

const props = defineProps<{
  partner: ScheduleRecord | null
  partnerSearching: boolean
  partnerError: string
  compareError: string
  comparing: boolean
}>()

const emit = defineEmits<{
  search: []
  back: []
  compare: []
}>()

const partnerName = defineModel<string>('partnerName')
const selectedWeek = ref<number | null>(null)

const weeks = computed(() => scheduleWeeks(props.partner?.slots ?? []))

watch(() => props.partner?.id, () => {
  selectedWeek.value = null
})
</script>

<template>
  <div class="mt-8 grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(19rem,0.48fr)]">
    <section class="glass-card min-w-0 p-5 sm:p-7">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p class="text-xs font-semibold uppercase tracking-[0.18em] text-blush">Find a classmate</p>
          <h2 class="mt-1 text-xl font-bold text-ink">找一位课搭子</h2>
          <p class="mt-1 text-sm text-sub">输入用户名，对比课程和个人日程的忙闲时间。</p>
        </div>
        <div class="flex h-12 w-12 items-center justify-center rounded-2xl bg-blush/15 text-2xl">🐾</div>
      </div>

      <div class="mt-6 flex flex-col gap-2 sm:flex-row">
        <div class="relative flex-1">
          <span class="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-faint">@</span>
          <input
            v-model="partnerName"
            class="input pl-9"
            placeholder="输入圈友用户名"
            autocomplete="off"
            :disabled="comparing"
            @keyup.enter="emit('search')"
          />
        </div>
        <button class="btn-primary sm:min-w-24" type="button" :disabled="partnerSearching || comparing" @click="emit('search')">
          <span v-if="partnerSearching" class="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white"></span>
          {{ partnerSearching ? '查找中' : '查找' }}
        </button>
      </div>
      <p class="mt-3 text-xs text-sub">对方需要主动公开课表。个人日程仅显示“已有安排”，不展示名称和地点；请确认你们使用的是同一学期、同一套节次。</p>

      <div v-if="partnerError" class="mt-5 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">{{ partnerError }}</div>

      <template v-if="partner">
        <div class="mt-6 flex items-center gap-3 rounded-2xl border border-primary-200 bg-primary-50/80 p-4">
          <UserAvatar :name="partner.owner?.display_name ?? ''" :size="46" />
          <div class="min-w-0 flex-1">
            <p class="truncate text-sm font-bold text-ink">{{ partner.owner?.display_name }}</p>
            <p class="mt-1 text-xs text-faint">@{{ partner.owner?.username }} · {{ partner.slots.length }} 个课程时段</p>
          </div>
          <span class="rounded-full bg-emerald-100 px-2.5 py-1 text-[11px] font-semibold text-emerald-700">已找到</span>
        </div>

        <div class="mt-5 space-y-4">
          <ScheduleWeekPicker v-model="selectedWeek" :weeks="weeks" />
          <ScheduleWeekGrid :slots="partner.slots" :timing="partner.timing" :week="selectedWeek" compact />
        </div>
      </template>

      <div v-else class="mt-6 flex min-h-[18rem] flex-col items-center justify-center rounded-3xl border border-dashed border-primary-200 bg-primary-50/35 px-6 text-center">
        <span class="text-4xl">🔎</span>
        <h3 class="mt-4 text-base font-bold text-ink">先搜索一位圈友</h3>
        <p class="mt-2 max-w-xs text-sm leading-6 text-sub">找到对方后，这里会显示 TA 的周课表预览，你可以先确认课程和地点。</p>
      </div>
    </section>

    <aside class="glass-card h-fit p-5 sm:p-6">
      <p class="text-xs font-semibold uppercase tracking-[0.18em] text-primary-500">Next step</p>
      <h2 class="mt-1 text-lg font-bold text-ink">准备好了吗？</h2>
      <p class="mt-2 text-sm leading-6 text-sub">点击开始对比，我们会帮你找出共同空闲、同教室和时间冲突。</p>

      <div class="mt-5 space-y-3">
        <div class="flex gap-3 rounded-2xl bg-emerald-50 p-3">
          <span class="text-lg">🌿</span>
          <div><p class="text-xs font-semibold text-emerald-800">共同空闲</p><p class="mt-1 text-[11px] leading-4 text-emerald-700/80">找适合约饭、出门或一起玩的时间</p></div>
        </div>
        <div class="flex gap-3 rounded-2xl bg-amber-50 p-3">
          <span class="text-lg">📍</span>
          <div><p class="text-xs font-semibold text-amber-800">同教室</p><p class="mt-1 text-[11px] leading-4 text-amber-700/80">发现你们可能在同一间教室的时段</p></div>
        </div>
      </div>

      <div v-if="compareError" class="mt-5 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-xs leading-5 text-red-600">{{ compareError }}</div>

      <div class="mt-6 flex flex-col gap-2">
        <button class="btn-primary w-full" type="button" :disabled="!partner || comparing" :class="{ 'cursor-not-allowed opacity-50': !partner || comparing }" @click="emit('compare')">
          <span v-if="comparing" class="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white"></span>
          {{ comparing ? '正在对比…' : '开始对比' }}
        </button>
        <button class="btn-ghost w-full !py-2.5 text-xs" type="button" :disabled="comparing" @click="emit('back')">返回我的课表</button>
      </div>
    </aside>
  </div>
</template>
