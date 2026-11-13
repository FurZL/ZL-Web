<script setup lang="ts">
import { computed } from 'vue'
import type { BlockProps } from './types'
import { str } from './types'

const props = defineProps<BlockProps>()
const key = computed(() => str(props.block, 'object_key'))
const caption = computed(() => str(props.block, 'caption'))
const item = computed(() => (key.value ? props.media[key.value] : undefined))
const src = computed(() => item.value?.display_url ?? item.value?.thumb_url ?? null)
</script>

<template>
  <div class="relative h-full overflow-hidden rounded-xl2 bg-primary-50">
    <img
      v-if="src"
      :src="src"
      :alt="caption || '主图'"
      class="w-full aspect-[16/9] object-cover"
      loading="lazy"
    />
    <div v-else class="w-full aspect-[16/9] flex flex-col items-center justify-center gap-1 text-faint">
      <span class="text-2xl">🖼</span>
      <span class="text-xs">{{ key ? '这张图片当前不可见' : '还没有选择主图' }}</span>
    </div>
    <p
      v-if="caption"
      class="absolute inset-x-0 bottom-0 px-4 py-3 text-sm text-white bg-gradient-to-t from-ink/70 to-transparent"
    >{{ caption }}</p>
  </div>
</template>
