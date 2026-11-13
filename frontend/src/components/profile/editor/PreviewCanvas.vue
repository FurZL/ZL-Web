<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ProfileBlock, ProfileMedia, ProfileTheme } from '@/types'
import {
  BLOCK_COMPONENTS,
  FLUSH_TYPES,
  SPAN_CLASS,
  isBlockType,
  normalizeSpan,
} from '../blocks/registry'
import { backgroundStyle, cardSurface, imageLayerStyle, themeVars } from '../theme'

const props = defineProps<{
  blocks: ProfileBlock[]
  selectedId: string | null
  theme: ProfileTheme
  media: Record<string, ProfileMedia>
  stats: { joined_days: number; gallery_image_count: number }
  backgroundUrl?: string | null
}>()

const emit = defineEmits<{
  select: [id: string | null]
  move: [from: number, to: number]
  remove: [id: string]
  duplicate: [id: string]
}>()

const dragFrom = ref<number | null>(null)
const dragOver = ref<number | null>(null)

function onDragStart(e: DragEvent, index: number) {
  dragFrom.value = index
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', String(index))
  }
}

function onDragOver(e: DragEvent, index: number) {
  if (dragFrom.value === null) return
  e.preventDefault()
  if (e.dataTransfer) e.dataTransfer.dropEffect = 'move'
  dragOver.value = index
}

function onDrop(index: number) {
  const from = dragFrom.value
  dragFrom.value = null
  dragOver.value = null
  if (from === null || from === index) return
  emit('move', from, index)
}

function onDragEnd() {
  dragFrom.value = null
  dragOver.value = null
}

function isFlush(block: ProfileBlock): boolean {
  return FLUSH_TYPES.has(block.type)
}

/** 未知类型不给宽度保证，退回整行，避免编辑器与渲染器对不齐 */
function spanClass(block: ProfileBlock): string {
  if (!isBlockType(block.type)) return SPAN_CLASS[12]
  return SPAN_CLASS[normalizeSpan(block.type, block.span)]
}

function componentFor(block: ProfileBlock) {
  return isBlockType(block.type) ? BLOCK_COMPONENTS[block.type] : null
}

const rootStyle = computed(() => [themeVars(props.theme), backgroundStyle(props.theme)])

function surface(block: ProfileBlock): Record<string, string> {
  if (isFlush(block)) return { border: '1px dashed rgba(31,27,51,0.12)' }
  return cardSurface(props.theme)
}
</script>

<template>
  <div class="relative overflow-hidden rounded-xl2 min-h-[520px]" :style="rootStyle" @click.self="emit('select', null)">
    <template v-if="theme.background_type === 'image' && backgroundUrl">
      <img :src="backgroundUrl" alt="" aria-hidden="true" class="absolute inset-0 w-full h-full pointer-events-none" :style="imageLayerStyle(theme)" />
      <div class="absolute inset-0 pointer-events-none bg-white/55"></div>
    </template>

    <div class="relative p-4">
      <div v-if="!blocks.length" class="py-24 text-center">
        <div class="text-4xl">🧩</div>
        <p class="mt-4 text-sm text-sub">从左侧模块库添加第一块内容</p>
        <p class="mt-1 text-xs text-faint">添加后可以改宽度、调顺序、填内容</p>
      </div>

      <div v-else class="grid grid-cols-12 gap-3">
        <div
          v-for="(block, index) in blocks"
          :key="block.id"
          :class="[
            spanClass(block),
            'relative group transition',
            selectedId === block.id ? 'ring-2 ring-primary ring-offset-2 ring-offset-transparent rounded-xl2' : '',
            dragOver === index && dragFrom !== null && dragFrom !== index ? 'ring-2 ring-blush rounded-xl2' : '',
            dragFrom === index ? 'opacity-40' : '',
          ]"
          :draggable="true"
          @dragstart="onDragStart($event, index)"
          @dragover="onDragOver($event, index)"
          @drop="onDrop(index)"
          @dragend="onDragEnd"
          @click.stop="emit('select', block.id)"
        >
          <div class="pointer-events-none select-none p-4 h-full" :style="surface(block)">
            <component
              :is="componentFor(block)"
              v-if="componentFor(block)"
              :block="block"
              :media="media"
              :stats="stats"
            />
            <div v-else class="text-xs text-blush">不支持的模块类型：{{ block.type }}</div>
          </div>

          <!-- 悬浮工具条：触屏上拖拽不可用，这里提供等价的顺序操作 -->
          <div class="absolute -top-2.5 right-2 flex items-center gap-1 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition">
            <button class="chip" title="上移" :disabled="index === 0" @click.stop="emit('move', index, index - 1)">↑</button>
            <button class="chip" title="下移" :disabled="index === blocks.length - 1" @click.stop="emit('move', index, index + 1)">↓</button>
            <button class="chip" title="复制" @click.stop="emit('duplicate', block.id)">⧉</button>
            <button class="chip chip-danger" title="删除" @click.stop="emit('remove', block.id)">✕</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chip {
  @apply w-6 h-6 rounded-full bg-white border border-primary-100 text-[11px] text-sub shadow-glass transition
    hover:text-ink hover:border-primary-300 disabled:opacity-30 disabled:cursor-not-allowed;
}
.chip-danger {
  @apply text-blush hover:text-red-500 hover:border-red-200;
}
</style>
