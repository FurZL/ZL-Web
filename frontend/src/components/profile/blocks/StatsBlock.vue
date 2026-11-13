<script setup lang="ts">
import { computed } from 'vue'
import type { BlockProps } from './types'
import { STAT_LABELS, strList } from './types'

const props = defineProps<BlockProps>()

const items = computed(() =>
  strList(props.block, 'items')
    .filter((k) => k in STAT_LABELS)
    .slice(0, 2)
    .map((k) => ({
      key: k,
      label: STAT_LABELS[k].label,
      value: k === 'joined_days' ? props.stats.joined_days : props.stats.gallery_image_count,
      unit: STAT_LABELS[k].unit,
    })),
)
</script>

<template>
  <div v-if="items.length" class="flex items-center gap-6 h-full">
    <div v-for="it in items" :key="it.key" class="flex-1 min-w-0">
      <p class="text-2xl font-bold leading-none" :style="{ color: 'var(--profile-primary)' }">
        {{ it.value }}<span class="ml-1 text-xs font-medium text-faint">{{ it.unit }}</span>
      </p>
      <p class="mt-1.5 text-xs text-faint truncate">{{ it.label }}</p>
    </div>
  </div>
  <div v-else class="text-sm text-faint">还没有选择数据项</div>
</template>
