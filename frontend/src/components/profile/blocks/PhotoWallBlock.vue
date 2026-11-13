<script setup lang="ts">
import { computed } from 'vue'
import type { BlockProps } from './types'
import { num, strList } from './types'

const props = defineProps<BlockProps>()
const keys = computed(() => strList(props.block, 'object_keys').slice(0, 12))

const gridClass = computed(() =>
  num(props.block, 'columns', 3) === 2
    ? 'grid grid-cols-2 gap-2'
    : 'grid grid-cols-2 md:grid-cols-3 gap-2',
)

const cells = computed(() =>
  keys.value.map((k) => ({
    key: k,
    src: props.media[k]?.thumb_url ?? props.media[k]?.display_url ?? null,
  })),
)
</script>

<template>
  <div v-if="cells.length" :class="gridClass">
    <div
      v-for="c in cells"
      :key="c.key"
      class="relative aspect-square overflow-hidden rounded-xl bg-primary-50"
    >
      <img v-if="c.src" :src="c.src" alt="" class="w-full h-full object-cover" loading="lazy" />
      <div v-else class="w-full h-full flex items-center justify-center text-[10px] text-faint">
        不可见
      </div>
    </div>
  </div>
  <div v-else class="text-sm text-faint">还没有往里放照片</div>
</template>
