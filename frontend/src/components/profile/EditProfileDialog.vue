<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { request } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import UserAvatar from '@/components/UserAvatar.vue'
import AvatarCropDialog from './AvatarCropDialog.vue'

const props = defineProps<{ show: boolean }>()
const emit = defineEmits<{ close: [] }>()

const auth = useAuthStore()
const editName = ref('')
const editBio = ref('')
const editError = ref('')
const saving = ref(false)

// 头像：裁剪流程
const fileInput = ref<HTMLInputElement | null>(null)
const cropShow = ref(false)
const cropFile = ref<File | null>(null)
const croppedBlob = ref<Blob | null>(null)
const croppedPreviewUrl = ref('')
const avatarUploading = ref(false)

const currentAvatar = computed(() => croppedPreviewUrl.value || auth.user?.avatar || '')

watch(() => props.show, (val) => {
  if (val) {
    editName.value = auth.user?.displayName ?? ''
    editBio.value = auth.user?.bio ?? ''
    editError.value = ''
    cropFile.value = null
    croppedBlob.value = null
    if (croppedPreviewUrl.value) {
      URL.revokeObjectURL(croppedPreviewUrl.value)
      croppedPreviewUrl.value = ''
    }
  }
})

function pickAvatar() {
  fileInput.value?.click()
}

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  const allowed = ['image/jpeg', 'image/png', 'image/webp', 'image/gif', 'image/avif']
  if (!allowed.includes(file.type)) {
    editError.value = '仅支持 JPG / PNG / WebP / GIF / AVIF 图片'
    return
  }
  if (file.size > 10 * 1024 * 1024) {
    editError.value = '图片大小不能超过 10MB'
    return
  }

  cropFile.value = file
  cropShow.value = true
  input.value = ''
}

function onCropConfirm(blob: Blob) {
  cropShow.value = false
  croppedBlob.value = blob
  if (croppedPreviewUrl.value) URL.revokeObjectURL(croppedPreviewUrl.value)
  croppedPreviewUrl.value = URL.createObjectURL(blob)
}

function onCropCancel() {
  cropShow.value = false
  cropFile.value = null
}

async function uploadAvatar() {
  if (!croppedBlob.value) return
  avatarUploading.value = true
  try {
    // 裁剪后的 Blob → File
    const file = new File([croppedBlob.value], 'avatar.jpg', { type: 'image/jpeg' })

    const intent = await request<{ upload_url: string; object_key: string; bucket: string }>({
      method: 'POST',
      url: '/profile/me/avatar/upload-intent',
      data: {
        filename: file.name,
        mime_type: file.type,
        size_bytes: file.size,
      },
    })

    const putResp = await fetch(intent.upload_url, {
      method: 'PUT',
      headers: { 'Content-Type': file.type },
      body: file,
    })
    if (!putResp.ok) throw new Error('上传失败，请重试')

    await request({
      method: 'POST',
      url: '/profile/me/avatar/upload-complete',
      data: { object_key: intent.object_key, bucket: intent.bucket },
    })

    croppedBlob.value = null
  } catch (e) {
    throw e
  } finally {
    avatarUploading.value = false
  }
}

async function removeAvatar() {
  try {
    await request({ method: 'DELETE', url: '/profile/me/avatar' })
    croppedBlob.value = null
    if (croppedPreviewUrl.value) {
      URL.revokeObjectURL(croppedPreviewUrl.value)
      croppedPreviewUrl.value = ''
    }
    await auth.fetchMe()
  } catch (e) {
    editError.value = e instanceof Error ? e.message : '删除失败'
  }
}

async function saveProfile() {
  if (!editName.value.trim()) {
    editError.value = '昵称不能为空'
    return
  }
  saving.value = true
  editError.value = ''
  try {
    if (croppedBlob.value) {
      await uploadAvatar()
    }
    await request({
      method: 'PUT',
      url: '/profile/me',
      data: { display_name: editName.value.trim(), bio: editBio.value.trim() },
    })
    await auth.fetchMe()
    emit('close')
  } catch (e) {
    editError.value = e instanceof Error ? e.message : '保存失败'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <div v-if="show" class="dialog-overlay" @click.self="emit('close')">
      <div class="glass-card p-6 w-full max-w-md max-h-[90vh] overflow-y-auto">
        <h2 class="text-lg font-bold text-ink">编辑资料</h2>
        <div v-if="editError" class="mt-3 text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{{ editError }}</div>

        <!-- 头像区 -->
        <div class="mt-5 flex flex-col items-center gap-3">
          <UserAvatar :name="editName || auth.user?.displayName || '?'" :size="80" :src="currentAvatar" />
          <div class="flex gap-2">
            <button class="btn-ghost text-xs px-3 py-1.5" @click="pickAvatar">
              {{ croppedBlob ? '重新选择' : '更换头像' }}
            </button>
            <button
              v-if="auth.user?.avatar || croppedBlob"
              class="text-xs px-3 py-1.5 rounded-lg border border-red-200 text-red-500 hover:bg-red-50 transition"
              @click="removeAvatar"
            >
              移除
            </button>
          </div>
          <input ref="fileInput" type="file" accept="image/jpeg,image/png,image/webp,image/gif,image/avif" class="hidden" @change="onFileChange" />
          <p v-if="croppedBlob" class="text-xs text-primary-700">已裁剪为 128×128，保存时上传</p>
        </div>

        <div class="mt-5 space-y-4">
          <div>
            <label class="label">昵称</label>
            <input v-model="editName" class="input" placeholder="大家怎么称呼你" maxlength="64" />
          </div>
          <div>
            <label class="label">简介</label>
            <textarea v-model="editBio" class="input min-h-[80px]" rows="3" placeholder="介绍一下自己…" maxlength="500"></textarea>
          </div>
        </div>

        <div class="mt-6 flex gap-3">
          <button class="btn-ghost flex-1" :disabled="saving" @click="emit('close')">取消</button>
          <button class="btn-primary flex-1" :disabled="saving" @click="saveProfile">
            {{ saving ? '保存中…' : '保存' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>

  <!-- 裁剪弹窗 -->
  <AvatarCropDialog :show="cropShow" :file="cropFile" @confirm="onCropConfirm" @cancel="onCropCancel" />
</template>
