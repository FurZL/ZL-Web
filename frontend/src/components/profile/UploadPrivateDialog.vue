<script setup lang="ts">
import { ref, watch } from 'vue'
import { request } from '@/api/client'
import type { UploadIntent } from '@/types'

const props = defineProps<{ show: boolean }>()
const emit = defineEmits<{ close: []; uploaded: [] }>()

const file = ref<File | null>(null)
const filePreview = ref('')
const description = ref('')
const uploading = ref(false)
const uploadError = ref('')

watch(() => props.show, (val) => {
  if (val) resetUpload()
})

function resetUpload() {
  file.value = null
  filePreview.value = ''
  description.value = ''
  uploadError.value = ''
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
      url: '/profile/me/images/upload-intent',
      data: { filename: file.value.name, mime_type: file.value.type || 'image/jpeg', size_bytes: file.value.size },
    })
    await fetch(intent.upload_url, {
      method: 'PUT',
      headers: { 'Content-Type': file.value.type || 'image/jpeg' },
      body: file.value,
    })
    await request({
      method: 'POST',
      url: '/profile/me/images/upload-complete',
      data: {
        bucket: intent.bucket,
        object_key: intent.object_key,
        original_name: file.value.name,
        description: description.value || null,
      },
    })
    emit('uploaded')
    emit('close')
  } catch (e) {
    uploadError.value = e instanceof Error ? e.message : '上传失败'
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
          <h2 class="text-xl font-bold text-ink">上传私有图片</h2>
          <button class="text-faint hover:text-ink" @click="emit('close')">✕</button>
        </div>

        <label class="mt-6 border-2 border-dashed rounded-xl2 p-8 text-center hover:border-primary-400 transition cursor-pointer block"
          :class="file ? 'border-emerald-300' : 'border-primary-200'">
          <input type="file" accept="image/*" class="hidden" @change="onFileChange" />
          <template v-if="file">
            <img :src="filePreview" alt="预览" class="max-h-40 mx-auto rounded-lg object-contain" />
            <p class="mt-3 text-sm text-ink">{{ file.name }}</p>
          </template>
          <template v-else>
            <div class="w-12 h-12 mx-auto rounded-full bg-primary-50 flex items-center justify-center text-2xl text-primary">＋</div>
            <p class="mt-3 text-sm text-sub">点击选择图片</p>
            <p class="mt-1 text-xs text-faint">仅自己可见</p>
          </template>
        </label>

        <div class="mt-5">
          <label class="label">描述（可选）</label>
          <input v-model="description" class="input" placeholder="给这张照片写点描述" />
        </div>

        <div v-if="uploadError" class="mt-4 text-sm text-blush bg-blush/10 rounded-lg px-4 py-2.5">{{ uploadError }}</div>

        <div class="mt-6 flex gap-3">
          <button class="btn-ghost flex-1" :disabled="uploading" @click="emit('close')">取消</button>
          <button class="btn-primary flex-1" :disabled="uploading" @click="doUpload">
            {{ uploading ? '上传中…' : '确认上传' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
