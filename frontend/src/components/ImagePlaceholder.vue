<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  title: string
  aspect?: string // 例如 '3/4'
  src?: string | null
}>()

const gradients = [
  ['#6B5CE7', '#B8AEEF'],
  ['#F0A6C8', '#F5C7DD'],
  ['#5BC0BE', '#A8E6CF'],
  ['#F4A261', '#FAD2A6'],
  ['#7B6CF0', '#C3B8FF'],
  ['#E282B0', '#F2B5D4'],
]

const idx = computed(() => {
  let h = 0
  for (const ch of props.title) h = (h * 131 + ch.charCodeAt(0)) % 1009
  return h % gradients.length
})

const bg = computed(() => {
  const [a, b] = gradients[idx.value]
  return `linear-gradient(135deg, ${a}, ${b})`
})
</script>

<template>
  <div class="relative w-full overflow-hidden" :style="{ aspectRatio: aspect ?? '1 / 1', background: src ? 'transparent' : bg }">
    <!-- 真实图片 -->
    <img v-if="src" :src="src" :alt="title" class="absolute inset-0 w-full h-full object-cover" loading="lazy" />
    <!-- 占位渐变 + 光斑 -->
    <template v-else>
      <div class="absolute -top-6 -left-6 w-24 h-24 rounded-full bg-white/25 blur-xl"></div>
      <div class="absolute bottom-4 right-4 w-20 h-20 rounded-full bg-white/15 blur-lg"></div>
    </template>
  </div>
</template>