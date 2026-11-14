<script setup lang="ts">
import { computed, ref } from 'vue'

const props = defineProps<{
  name: string
  size?: number
  src?: string | null
}>()

const imgError = ref(false)

const palette = [
  ['#6B5CE7', '#B8AEEF'],
  ['#F0A6C8', '#F5C7DD'],
  ['#5BC0BE', '#A8E6CF'],
  ['#F4A261', '#FAD2A6'],
]

const idx = computed(() => {
  let h = 0
  for (const ch of props.name) h = (h * 31 + ch.charCodeAt(0)) % 997
  return h % palette.length
})
const bg = computed(() => {
  const [a, b] = palette[idx.value]
  return `linear-gradient(135deg, ${a}, ${b})`
})
const initial = computed(() => props.name.trim().charAt(0) || '?')
const sizePx = computed(() => `${props.size ?? 40}px`)

const showImage = computed(() => !!props.src && !imgError.value)
</script>

<template>
  <div
    class="rounded-full flex items-center justify-center text-white font-semibold select-none shrink-0 overflow-hidden"
    :style="{
      width: sizePx,
      height: sizePx,
      background: showImage ? '#eee' : bg,
      fontSize: `${Math.round((props.size ?? 40) * 0.42)}px`,
    }"
  >
    <img
      v-if="showImage"
      :src="props.src!"
      :alt="props.name"
      class="w-full h-full object-cover"
      @error="imgError = true"
    />
    <span v-else>{{ initial }}</span>
  </div>
</template>
