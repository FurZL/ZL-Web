<script setup lang="ts">
import { computed } from 'vue'
import type { BlockProps } from './types'
import { num, strList } from './types'

const props = defineProps<BlockProps>()
const keys = computed(() => strList(props.block, 'object_keys').slice(0, 12))

const gridClass = computed(() =>
  num(props.block, 'columns', 3) === 2
    ? 'columns-2 gap-2'
    : 'columns-2 md:columns-3 gap-2',
)

const cells = computed(() =>
  keys.value.map((key) => {
    const item = props.media[key]
    return {
      key,
      src: item?.thumb_url ?? item?.display_url ?? null,
      width: item?.width ?? null,
      height: item?.height ?? null,
    }
  }),
)
</script>

<template>
  <div v-if="cells.length" :class="gridClass">
    <div
      v-for="c in cells"
      :key="c.key"
      class="mb-2 break-inside-avoid overflow-hidden rounded-xl bg-primary-50"
    >
      <img
        v-if="c.src"
        :src="c.src"
        :width="c.width ?? undefined"
        :height="c.height ?? undefined"
        alt=""
        class="block h-auto w-full"
        loading="lazy"
      />
      <div v-else class="aspect-[4/3] flex items-center justify-center text-[10px] text-faint">
        不可见
      </div>
    </div>
  </div>
  <div v-else class="text-sm text-faint">还没有往里放照片</div>
</template>
