<script setup lang="ts">
import { computed } from 'vue'
import type { ProfileBlock, ProfileMedia, ProfileTheme } from '@/types'
import { BLOCK_COMPONENTS, FLUSH_TYPES, SPAN_CLASS, isBlockType, normalizeSpan } from './blocks/registry'
import { backgroundStyle, cardSurface, imageLayerStyle, themeVars } from './theme'

const props = defineProps<{
  theme: ProfileTheme
  blocks: ProfileBlock[]
  media: Record<string, ProfileMedia>
  stats: { joined_days: number; gallery_image_count: number }
  /** 背景图为 image 类型时，由父组件从 media 里解出来的地址 */
  backgroundUrl?: string | null
}>()

// 未知 type 一律跳过并可提示，不做部分渲染——与 DynamicPage 的既有做法一致
const known = computed(() => props.blocks.filter((b) => isBlockType(b.type)))
const ignored = computed(() => props.blocks.length - known.value.length)

function spanClass(block: ProfileBlock): string {
  return SPAN_CLASS[normalizeSpan(block.type, block.span)]
}

function componentFor(block: ProfileBlock) {
  return BLOCK_COMPONENTS[block.type]
}

function blockStyle(block: ProfileBlock): Record<string, string> {
  if (FLUSH_TYPES.has(block.type)) return {}
  return cardSurface(props.theme)
}

function isFlush(block: ProfileBlock): boolean {
  return FLUSH_TYPES.has(block.type)
}
</script>

<template>
  <div class="relative overflow-hidden rounded-xl2" :style="[themeVars(theme), backgroundStyle(theme)]">
    <!-- 图片背景层：单独一层，模糊不影响内容 -->
    <template v-if="theme.background_type === 'image' && backgroundUrl">
      <img
        :src="backgroundUrl"
        alt=""
        aria-hidden="true"
        class="absolute inset-0 w-full h-full pointer-events-none"
        :style="imageLayerStyle(theme)"
      />
      <div class="absolute inset-0 pointer-events-none bg-white/55"></div>
    </template>

    <div class="relative p-4 sm:p-6">
      <p v-if="ignored > 0" class="mb-4 text-xs text-faint">{{ ignored }} 个未知组件已被忽略</p>

      <div v-if="known.length" class="grid grid-cols-12 gap-4">
        <div
          v-for="block in known"
          :key="block.id"
          :class="[spanClass(block), isFlush(block) ? '' : 'p-5']"
          :style="blockStyle(block)"
        >
          <component
            :is="componentFor(block)"
            :block="block"
            :media="media"
            :stats="stats"
          />
        </div>
      </div>

      <div v-else class="py-12 text-center text-sm text-faint">
        主页还是空的
      </div>
    </div>
  </div>
</template>
