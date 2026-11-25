<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    weeks: number[]
    modelValue: number | null
    compact?: boolean
  }>(),
  { modelValue: null, compact: false },
)

const emit = defineEmits<{
  'update:modelValue': [value: number | null]
}>()

const selected = computed({
  get: () => props.modelValue,
  set: (value: number | null) => emit('update:modelValue', value),
})

function move(delta: number) {
  if (!props.weeks.length) return
  if (selected.value === null) {
    selected.value = delta > 0 ? props.weeks[0] : props.weeks[props.weeks.length - 1]
    return
  }
  const index = props.weeks.indexOf(selected.value)
  const next = Math.max(0, Math.min(props.weeks.length - 1, index + delta))
  selected.value = props.weeks[next]
}
</script>

<template>
  <div v-if="compact" class="week-picker week-picker--compact">
    <div class="flex flex-wrap items-center gap-2">
      <button type="button" class="week-compact__arrow" aria-label="上一周" @click="move(-1)">‹</button>
      <select v-model="selected" class="week-compact__select" aria-label="选择查看周次">
        <option :value="null">全学期</option>
        <option v-for="week in weeks" :key="week" :value="week">第 {{ week }} 周</option>
      </select>
      <button type="button" class="week-compact__arrow" aria-label="下一周" @click="move(1)">›</button>
      <span class="text-[11px] text-faint">{{ selected === null ? '查看全部周次' : `第 ${selected} 周` }}</span>
    </div>
  </div>

  <div v-else class="week-picker">
    <div class="flex items-center justify-between gap-3 mb-3">
      <div>
        <p class="text-sm font-semibold text-ink">查看哪一周</p>
        <p class="text-xs text-faint mt-0.5">切换周次，课程卡片会同步更新</p>
      </div>
      <span class="week-picker__current">
        {{ selected === null ? '学期总览' : `第 ${selected} 周` }}
      </span>
    </div>

    <div class="flex gap-2 overflow-x-auto pb-1 scrollbar-thin">
      <button
        type="button"
        class="week-chip week-chip--all"
        :class="{ 'week-chip--active': selected === null }"
        :aria-pressed="selected === null"
        @click="selected = null"
      >
        <span class="text-[10px] uppercase tracking-wide">All</span>
        <span>全学期</span>
      </button>
      <button
        v-for="week in weeks"
        :key="week"
        type="button"
        class="week-chip"
        :class="{ 'week-chip--active': selected === week }"
        :aria-pressed="selected === week"
        @click="selected = week"
      >
        <span class="text-[10px] text-current/60">W{{ String(week).padStart(2, '0') }}</span>
        <span>第 {{ week }} 周</span>
      </button>
    </div>

    <p v-if="!weeks.length" class="mt-3 text-xs text-faint">
      这份课表没有记录具体周次，将按整学期显示。
    </p>
  </div>
</template>

<style scoped>
.week-picker {
  border: 1px solid rgba(107, 92, 231, 0.12);
  border-radius: 1rem;
  padding: 1rem;
  background: rgba(255, 255, 255, 0.48);
}

.week-picker__current {
  color: #493db0;
  background: #f4f3fb;
  border: 1px solid #d6d1f5;
  border-radius: 999px;
  padding: 0.35rem 0.7rem;
  font-size: 0.7rem;
  font-weight: 600;
  white-space: nowrap;
}

.week-chip {
  display: inline-flex;
  min-width: 4.75rem;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.1rem;
  border: 1px solid rgba(107, 92, 231, 0.12);
  border-radius: 0.8rem;
  background: rgba(255, 255, 255, 0.68);
  color: #6e698c;
  padding: 0.55rem 0.7rem;
  font-size: 0.72rem;
  line-height: 1.25;
  transition: 0.2s ease;
  white-space: nowrap;
}

.week-chip:hover {
  border-color: #b8aeef;
  color: #493db0;
  transform: translateY(-1px);
}

.week-chip--active {
  border-color: #6b5ce7;
  background: #6b5ce7;
  color: white;
  box-shadow: 0 8px 18px rgba(107, 92, 231, 0.2);
}

.week-chip--active:hover {
  color: white;
}

.week-chip--all {
  min-width: 4.4rem;
}

.week-picker--compact {
  padding: 0.55rem 0.7rem;
  border-radius: 0.8rem;
  background: rgba(255, 255, 255, 0.62);
}

.week-compact__arrow {
  display: inline-flex;
  height: 2rem;
  width: 2rem;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(107, 92, 231, 0.14);
  border-radius: 0.6rem;
  background: white;
  color: #493db0;
  font-size: 1rem;
  line-height: 1;
}

.week-compact__arrow:hover {
  background: #f4f3fb;
}

.week-compact__select {
  min-width: 8rem;
  border: 1px solid rgba(107, 92, 231, 0.14);
  border-radius: 0.6rem;
  background: white;
  color: #493db0;
  padding: 0.35rem 0.6rem;
  font-size: 0.78rem;
  font-weight: 600;
}
</style>
