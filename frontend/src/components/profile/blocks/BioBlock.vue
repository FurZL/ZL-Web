<script setup lang="ts">
import { computed } from 'vue'
import type { BlockProps } from './types'
import { str } from './types'

const props = defineProps<BlockProps>()
const text = computed(() => str(props.block, 'text'))
</script>

<template>
  <div class="h-full">
    <p v-if="text" class="whitespace-pre-wrap text-sm leading-relaxed text-sub break-words">{{ text }}</p>
    <p v-else class="text-sm text-faint">还没有写简介</p>
  </div>
</template>
