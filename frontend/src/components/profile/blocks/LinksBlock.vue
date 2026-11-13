<script setup lang="ts">
import { computed } from 'vue'
import type { ProfileLinkItem } from '@/types'
import type { BlockProps } from './types'

const props = defineProps<BlockProps>()

function safeItems(raw: unknown): ProfileLinkItem[] {
  if (!Array.isArray(raw)) return []
  return raw
    .filter((x): x is Record<string, unknown> => typeof x === 'object' && x !== null)
    .map((x) => ({
      label: typeof x.label === 'string' ? x.label : '',
      url: typeof x.url === 'string' ? x.url : '',
    }))
    .filter((x) => x.label && /^https:\/\//i.test(x.url))
}

const items = computed(() => safeItems(props.block.props.items).slice(0, 8))
</script>

<template>
  <div v-if="items.length" class="space-y-2">
    <a
      v-for="(item, i) in items"
      :key="i"
      :href="item.url"
      target="_blank"
      rel="noopener noreferrer nofollow"
      class="flex items-center gap-2 text-sm text-sub hover:text-ink transition truncate"
    >
      <span class="w-1.5 h-1.5 rounded-full shrink-0" :style="{ background: 'var(--profile-accent)' }"></span>
      <span class="truncate">{{ item.label }}</span>
    </a>
  </div>
  <div v-else class="text-sm text-faint">还没有添加链接</div>
</template>
