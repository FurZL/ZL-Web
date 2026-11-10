<script setup lang="ts">
import { ref, watch } from 'vue'
import { request } from '@/api/client'
import type { UploadIntent } from '@/types'

const props = defineProps<{
  show: boolean
}>()

const emit = defineEmits<{ close: []; uploaded: [] }>()

const file = ref<File | null>(null)
const filePreview = ref('')
const uploadTitle = ref('')
const uploadTags = ref('')
const uploading = ref(false)
const uploadError = ref('')
const uploaded = ref(false)

watch(() => props.show, (val) => {
  if (val) resetUpload()
})

function resetUpload() {
  file.value = null
  filePreview.value = ''
  uploadTitle.value = ''
  uploadTags.value = ''
  uploadError.value = ''
  uploaded.value = false
}

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  const f = input.files?.[0]
  if (!f) return
  if (!f.type.startsWith('image/')) {
    uploadError.value = '请选择图片文件'
    return
  }
  file.value = f
  uploadError.value = ''
  filePreview.value = URL.createObjectURL(f)
  if (!uploadTitle.value) uploadTitle.value = f.name.replace(/\.[^.]+$/, '')
}

async function doUpload() {
  if (!file.value) {
    uploadError.value = '请先选择图片'
    return
  }
  uploading.value = true
  uploadError.value = ''
  try {
    const intent = await request<UploadIntent>({
      method: 'POST',
      url: '/images/upload-intent',
      data: {
        filename: file.value.name,
        mime_type: file.value.type || 'image/jpeg',
        size_bytes: file.value.size,
        purpose: 'gallery',
      },
    })
    await fetch(intent.upload_url, {
      method: 'PUT',
      headers: { 'Content-Type': file.value.type || 'image/jpeg' },
      body: file.value,
    })
    await request({
      method: 'POST',
      url: '/images/upload-complete',
      data: {
        bucket: intent.bucket,
        object_key: intent.object_key,
        purpose: 'gallery',
        original_name: file.value.name,
        description: uploadTitle.value || null,
        tags: uploadTags.value.split(/[,，]/).map((t) => t.trim()).filter(Boolean),
      },
    })
    uploaded.value = true
    emit('uploaded')
    setTimeout(() => emit('close'), 1200)
  } catch (e) {
    uploadError.value = e instanceof Error ? e.message : '上传失败，请重试'
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <div v-if="show" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/40 backdrop-blur-sm" @click.self="emit('close')">
      <div class="glass-card max-w-lg w-full p-8">
        <div class="flex items-center justify-between">
          <h2 class="text-xl font-bold text-ink">上传图片</h2>
          <button class="text-faint hover:text-ink" @click="emit('close')">✕</button>
        </div>

        <div v-if="!uploaded">
          <label class="mt-6 border-2 border-dashed rounded-xl2 p-8 text-center hover:border-primary-400 transition cursor-pointer block"
            :class="file ? 'border-emerald-300' : 'border-primary-200'">
            <input type="file" accept="image/*" class="hidden" @change="onFileChange" />
            <template v-if="file">
              <img :src="filePreview" alt="预览" class="max-h-40 mx-auto rounded-lg object-contain" />
              <p class="mt-3 text-sm text-ink">{{ file.name }}</p>
              <p class="mt-1 text-xs text-faint">{{ (file.size / 1024 / 1024).toFixed(2) }} MB</p>
            </template>
            <template v-else>
              <div class="w-12 h-12 mx-auto rounded-full bg-primary-50 flex items-center justify-center text-2xl text-primary">＋</div>
              <p class="mt-3 text-sm text-sub">点击选择图片</p>
              <p class="mt-1 text-xs text-faint">支持 JPG / PNG / WebP / GIF / AVIF</p>
            </template>
          </label>

          <div class="mt-5 space-y-4">
            <div>
              <label class="label">描述</label>
              <input v-model="uploadTitle" class="input" placeholder="给这张照片写点描述" />
            </div>
            <div>
              <label class="label">标签</label>
              <input v-model="uploadTags" class="input" placeholder="用逗号分隔，例如：日常, 校园" />
            </div>
          </div>

          <div v-if="uploadError" class="mt-4 text-sm text-blush bg-blush/10 rounded-lg px-4 py-2.5">{{ uploadError }}</div>

          <div class="mt-6 flex gap-3">
            <button class="btn-ghost flex-1" :disabled="uploading" @click="emit('close')">取消</button>
            <button class="btn-primary flex-1" :disabled="uploading" @click="doUpload">
              {{ uploading ? '上传中…' : '确认上传' }}
            </button>
          </div>
        </div>

        <div v-else class="py-16 text-center">
          <div class="w-14 h-14 mx-auto rounded-full bg-primary-50 flex items-center justify-center text-2xl text-primary">✓</div>
          <p class="mt-4 text-ink font-medium">上传成功</p>
          <p class="mt-1 text-sm text-sub">照片已发布到展示区</p>
        </div>
      </div>
    </div>
  </Teleport>
</template>
