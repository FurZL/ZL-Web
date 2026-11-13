<script setup lang="ts">
import { computed } from 'vue'
import type { BlockProps } from './types'
import { str } from './types'

const props = defineProps<BlockProps>()
const tag = computed(() => str(props.block, 'tag').trim())
const label = computed(() => str(props.block, 'label') || '去看图')
const to = computed(() => (tag.value ? { path: '/gallery', query: { tag: tag.value } } : '/gallery'))
</script>

<template>
  <RouterLink
    :to="to"
    class="flex items-center gap-3 h-full rounded-xl px-4 py-3 transition hover:opacity-80"
    :style="{ background: 'var(--profile-primary-soft)' }"
  >
    <span class="text-xl">🖼</span>
    <span class="flex-1 min-w-0">
      <span class="block text-sm font-medium" :style="{ color: 'var(--profile-primary)' }">{{ label }}</span>
      <span class="block text-xs text-faint truncate">{{ tag ? `标签：${tag}` : '全部公开图片' }}</span>
    </span>
    <span class="text-faint">›</span>
  </RouterLink>
</template>
