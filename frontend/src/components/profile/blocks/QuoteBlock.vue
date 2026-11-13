<script setup lang="ts">
import { computed } from 'vue'
import type { BlockProps } from './types'
import { str } from './types'

const props = defineProps<BlockProps>()
const text = computed(() => str(props.block, 'text'))
const author = computed(() => str(props.block, 'author'))
</script>

<template>
  <div class="relative h-full pl-6">
    <span
      class="absolute -top-1 left-0 text-4xl leading-none select-none"
      :style="{ color: 'var(--profile-accent)' }"
      aria-hidden="true"
    >❝</span>
    <p v-if="text" class="text-base leading-relaxed text-ink break-words">{{ text }}</p>
    <p v-else class="text-sm text-faint">写一句话放在这里</p>
    <p v-if="author" class="mt-2 text-xs text-faint">— {{ author }}</p>
  </div>
</template>
