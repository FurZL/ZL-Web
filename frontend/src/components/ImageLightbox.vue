<script setup lang="ts">
defineProps<{
  open: boolean
  title: string
  imageUrl: string | null
  description?: string | null
  loading?: boolean
}>()

const emit = defineEmits<{ close: []; download: [] }>()
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/40 backdrop-blur-sm" @click.self="emit('close')">
      <div class="glass-card max-w-4xl w-full overflow-hidden max-h-[90vh] flex flex-col md:flex-row">
        <!-- 左侧大图 -->
        <div class="md:w-3/5 bg-white/30 flex items-center justify-center min-h-[240px]">
          <div v-if="loading" class="text-sub">加载中…</div>
          <img v-else-if="imageUrl" :src="imageUrl" :alt="title" class="w-full h-full max-h-[80vh] object-contain" />
          <div v-else class="text-faint text-sm">暂无图片</div>
        </div>

        <!-- 右侧信息 -->
        <div class="md:w-2/5 p-6 flex flex-col">
          <div class="flex items-start justify-between gap-2">
            <h2 class="text-xl font-bold text-ink break-all">{{ title }}</h2>
            <button class="text-faint hover:text-ink shrink-0" @click="emit('close')">✕</button>
          </div>

          <!-- 元信息插槽（摄影师/标签/日期等） -->
          <slot name="meta" />

          <p class="mt-4 text-sm text-sub leading-relaxed flex-1">
            {{ description || '这张照片还没有描述。' }}
          </p>

          <!-- 底部操作区（默认下载按钮，可用插槽覆盖） -->
          <div class="mt-6">
            <slot name="actions">
              <button class="btn-primary w-full" @click="emit('download')">下载原图</button>
            </slot>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>