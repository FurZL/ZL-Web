<script setup lang="ts">
import { computed } from 'vue'
import type { ProfileBlockType } from '@/types'
import { ALLOWED_SPANS, BLOCK_ICONS, BLOCK_LABELS } from '../blocks/registry'

const props = defineProps<{
  remaining: number
}>()

const emit = defineEmits<{ add: [type: ProfileBlockType] }>()

// 顺序即推荐程度：越靠上越常用
const LIBRARY: ProfileBlockType[] = [
  'bio',
  'quote',
  'featured_photo',
  'photo_wall',
  'gallery_link',
  'links',
  'stats',
  'html_block',
]

const full = computed(() => props.remaining <= 0)

function spanHint(type: ProfileBlockType): string {
  const spans = ALLOWED_SPANS[type]
  if (spans.length === 1) return '整行'
  return `${spans.length} 种宽度`
}
</script>

<template>
  <div class="glass-card p-4">
    <div class="flex items-baseline justify-between">
      <h2 class="text-sm font-semibold text-ink">模块库</h2>
      <span class="text-[11px]" :class="full ? 'text-blush' : 'text-faint'">
        {{ full ? '已达上限' : `还可加 ${remaining}` }}
      </span>
    </div>

    <div class="mt-3 space-y-1.5">
      <button
        v-for="type in LIBRARY"
        :key="type"
        class="w-full flex items-center gap-3 rounded-xl px-3 py-2.5 text-left transition border border-transparent"
        :class="full
          ? 'opacity-40 cursor-not-allowed'
          : 'hover:bg-primary-50 hover:border-primary-100 active:scale-[0.99]'"
        :disabled="full"
        @click="emit('add', type)"
      >
        <span class="w-7 h-7 shrink-0 rounded-lg bg-primary-50 flex items-center justify-center text-xs">{{ BLOCK_ICONS[type] }}</span>
        <span class="flex-1 min-w-0">
          <span class="block text-xs font-medium text-ink truncate">{{ BLOCK_LABELS[type] }}</span>
          <span class="block text-[10px] text-faint">{{ spanHint(type) }}</span>
        </span>
        <span class="text-faint text-sm">＋</span>
      </button>
    </div>

    <p class="mt-3 text-[11px] leading-relaxed text-faint">
      点击即可添加。模块之间用上移/下移或拖拽调整顺序，手机端统一整行显示。
    </p>
  </div>
</template>
