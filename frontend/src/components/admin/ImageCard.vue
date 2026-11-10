<script setup lang="ts">
import ImagePlaceholder from '@/components/ImagePlaceholder.vue'
import type { GalleryImage } from '@/types'
import { MODERATION_STATUS } from '@/utils/statusStyles'

defineProps<{
  image: GalleryImage
  acting: boolean
}>()

const emit = defineEmits<{
  preview: [image: GalleryImage]
  approve: [image: GalleryImage]
  reject: [image: GalleryImage]
  toggleVisibility: [image: GalleryImage]
  editTags: [image: GalleryImage]
  remove: [image: GalleryImage]
}>()

const statusMap = MODERATION_STATUS

function fmtDate(iso: string | null) {
  return iso ? new Date(iso).toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'
}
</script>

<template>
  <div class="glass-card p-2">
    <!-- 缩略图 -->
    <div class="rounded-xl overflow-hidden cursor-pointer group relative" @click="emit('preview', image)">
      <ImagePlaceholder
        :title="image.description || image.title"
        :src="image.thumb_url || image.display_url || image.url"
        aspect="1/1"
      />
      <span
        class="absolute top-2 left-2 text-[10px] font-medium rounded-full px-2 py-0.5"
        :class="statusMap[image.moderation_status]?.cls ?? 'bg-gray-100 text-gray-600'"
      >
        {{ statusMap[image.moderation_status]?.text ?? image.moderation_status }}
      </span>
      <span v-if="!image.is_public" class="absolute top-2 right-2 text-[10px] font-medium bg-ink/60 text-white rounded-full px-2 py-0.5">
        私有
      </span>
    </div>

    <!-- 信息 -->
    <div class="px-2 py-2">
      <p class="text-sm text-ink truncate">{{ image.description || image.title }}</p>
      <p class="text-xs text-faint mt-0.5 truncate">{{ image.photographer }} · {{ fmtDate(image.uploaded_at) }}</p>
      <div v-if="image.tags.length" class="mt-1 flex flex-wrap gap-1">
        <span v-for="t in image.tags.slice(0, 3)" :key="t" class="tag-badge-sm">{{ t }}</span>
      </div>
    </div>

    <!-- 操作按钮 -->
    <div class="px-2 pb-2 flex flex-wrap gap-1.5">
      <button
        v-if="image.moderation_status !== 'approved'"
        class="btn-xs-success"
        :disabled="acting"
        @click="emit('approve', image)"
      >
        通过
      </button>
      <button
        v-if="image.moderation_status !== 'rejected'"
        class="btn-xs-warning"
        :disabled="acting"
        @click="emit('reject', image)"
      >
        拒绝
      </button>
      <button
        class="btn-xs"
        :disabled="acting"
        @click="emit('toggleVisibility', image)"
      >
        {{ image.is_public ? '设为私有' : '设为公开' }}
      </button>
      <button
        class="btn-xs"
        @click="emit('editTags', image)"
      >
        标签
      </button>
      <button
        class="btn-xs-danger"
        :disabled="acting"
        @click="emit('remove', image)"
      >
        删除
      </button>
    </div>
  </div>
</template>
