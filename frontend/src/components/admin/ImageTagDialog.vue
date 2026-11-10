<script setup lang="ts">
import type { GalleryImage } from '@/types'

defineProps<{
  image: GalleryImage | null
  saving: boolean
}>()

const emit = defineEmits<{ close: []; save: [] }>()
const tagInput = defineModel<string>('tagInput', { required: true })
</script>

<template>
  <Teleport to="body">
    <div v-if="image" class="dialog-overlay" @click.self="emit('close')">
      <div class="glass-card p-6 w-full max-w-md">
        <h2 class="text-lg font-bold text-ink">编辑标签</h2>
        <p class="mt-1 text-xs text-faint">{{ image.description || image.title }}</p>
        <div class="mt-4">
          <label class="label">标签（逗号分隔）</label>
          <input v-model="tagInput" class="input" placeholder="例如：日常, 校园, 治愈" />
        </div>
        <div class="mt-6 flex gap-3">
          <button class="btn-ghost flex-1" @click="emit('close')">取消</button>
          <button class="btn-primary flex-1" :disabled="saving" @click="emit('save')">
            {{ saving ? '保存中…' : '保存' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
