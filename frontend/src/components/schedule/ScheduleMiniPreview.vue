<script setup lang="ts">
import { computed } from 'vue'
import type { ScheduleSlot, ScheduleTiming } from '@/types'

/** 课表架缩略图：把课程/日程按星期与节次比例画成小色块，不做交互。 */
const props = withDefaults(defineProps<{
  slots: ScheduleSlot[]
  timing?: ScheduleTiming | null
}>(), { timing: null })

const totalLessons = computed(() => {
  const timeline = props.timing?.periods.length ?? 0
  const used = props.slots.reduce((max, slot) => Math.max(max, slot.lesson_end), 0)
  return Math.max(12, timeline, used, 1)
})

const blocks = computed(() => props.slots.map((slot, index) => ({
  key: `${index}-${slot.weekday}-${slot.lesson_start}-${slot.lesson_end}`,
  kind: slot.kind ?? 'course',
  style: {
    left: `${(slot.weekday / 7) * 100}%`,
    width: `${100 / 7}%`,
    top: `${((slot.lesson_start - 1) / totalLessons.value) * 100}%`,
    height: `${((slot.lesson_end - slot.lesson_start + 1) / totalLessons.value) * 100}%`,
  },
})))

const separators = [1, 2, 3, 4, 5, 6]
</script>

<template>
  <div class="mini-preview" :class="{ 'mini-preview--empty': !slots.length }" aria-hidden="true">
    <span
      v-for="index in separators"
      :key="index"
      class="mini-preview__separator"
      :style="{ left: `${(index / 7) * 100}%` }"
    ></span>
    <span
      v-for="block in blocks"
      :key="block.key"
      class="mini-preview__block"
      :class="`mini-preview__block--${block.kind}`"
      :style="block.style"
    ></span>
    <span v-if="!slots.length" class="mini-preview__placeholder">空课表</span>
  </div>
</template>

<style scoped>
.mini-preview {
  position: relative;
  height: 4.6rem;
  overflow: hidden;
  border-radius: 0.55rem;
  background:
    linear-gradient(180deg, rgba(107, 92, 231, 0.06), rgba(107, 92, 231, 0.02)),
    repeating-linear-gradient(180deg, transparent 0 24%, rgba(107, 92, 231, 0.06) 24% 25%);
  border: 1px solid rgba(107, 92, 231, 0.1);
}

.mini-preview--empty {
  background: rgba(244, 243, 251, 0.6);
}

.mini-preview__separator {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 1px;
  background: rgba(107, 92, 231, 0.08);
}

.mini-preview__block {
  position: absolute;
  max-width: 100%;
  border: 1px solid rgba(255, 255, 255, 0.55);
  border-radius: 3px;
  background: rgba(107, 92, 231, 0.72);
}

.mini-preview__block--event {
  border: 1px dashed rgba(255, 255, 255, 0.75);
  background: rgba(15, 118, 110, 0.68);
}

.mini-preview__placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #a5a0c2;
  font-size: 0.62rem;
  letter-spacing: 0.08em;
}
</style>
