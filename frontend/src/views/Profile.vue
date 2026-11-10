<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import UserAvatar from '@/components/UserAvatar.vue'
import ImagePlaceholder from '@/components/ImagePlaceholder.vue'
import ImageLightbox from '@/components/ImageLightbox.vue'
import { request } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import type { ProfileImage, UploadIntent } from '@/types'

const route = useRoute()
const auth = useAuthStore()

const isSelf = computed(() => !route.params.username)

// 私有相册（仅本人）
const photos = ref<ProfileImage[]>([])
const loading = ref(false)
const loadError = ref('')

async function loadPhotos() {
  if (!isSelf.value) return
  loading.value = true
  loadError.value = ''
  try {
    const data = await request<{ items: ProfileImage[] }>({ method: 'GET', url: '/profile/me/images' })
    photos.value = data.items
  } catch (e) {
    loadError.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

// 上传
const showUpload = ref(false)
const file = ref<File | null>(null)
const filePreview = ref('')
const description = ref('')
const uploading = ref(false)
const uploadError = ref('')

function openUpload() {
  showUpload.value = true
}
function closeUpload() {
  if (!uploading.value) {
    showUpload.value = false
    resetUpload()
  }
}
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
    await loadPhotos()
    closeUpload()
  } catch (e) {
    uploadError.value = e instanceof Error ? e.message : '上传失败'
  } finally {
    uploading.value = false
  }
}

// 预览（lightbox）
const previewing = ref<ProfileImage | null>(null)
const previewUrl = ref('')
const previewLoading = ref(false)

async function openPreview(img: ProfileImage) {
  previewing.value = img
  previewUrl.value = ''
  previewLoading.value = true
  try {
    const data = await request<{ url: string }>({ method: 'GET', url: `/profile/me/images/${img.id}/url` })
    previewUrl.value = data.url
  } catch (e) {
    alert(e instanceof Error ? e.message : '打开失败')
    previewing.value = null
  } finally {
    previewLoading.value = false
  }
}

function closePreview() {
  previewing.value = null
  previewUrl.value = ''
}

async function downloadCurrent() {
  if (!previewing.value) return
  try {
    let url = previewUrl.value
    if (!url) {
      const data = await request<{ url: string }>({ method: 'GET', url: `/profile/me/images/${previewing.value.id}/url` })
      url = data.url
    }
    window.open(url, '_blank')
  } catch (e) {
    alert(e instanceof Error ? e.message : '下载失败')
  }
}

async function deleteFromPreview() {
  if (!previewing.value) return
  const img = previewing.value
  if (!confirm(`确定删除「${img.title ?? '这张图片'}」吗？`)) return
  try {
    await request({ method: 'DELETE', url: `/profile/me/images/${img.id}` })
    closePreview()
    await loadPhotos()
  } catch (e) {
    alert(e instanceof Error ? e.message : '删除失败')
  }
}

// 删除
const deletingId = ref<string | null>(null)
async function deletePhoto(img: ProfileImage) {
  if (!confirm(`确定删除「${img.title ?? '这张图片'}」吗？`)) return
  deletingId.value = img.id
  try {
    await request({ method: 'DELETE', url: `/profile/me/images/${img.id}` })
    await loadPhotos()
  } catch (e) {
    alert(e instanceof Error ? e.message : '删除失败')
  } finally {
    deletingId.value = null
  }
}

const profile = computed(() => {
  if (isSelf.value) return auth.user
  return null
})

// 编辑资料
const showEdit = ref(false)
const editName = ref('')
const editBio = ref('')
const editError = ref('')
const saving = ref(false)

function openEdit() {
  editName.value = auth.user?.displayName ?? ''
  editBio.value = auth.user?.bio ?? ''
  editError.value = ''
  showEdit.value = true
}

async function saveProfile() {
  if (!editName.value.trim()) {
    editError.value = '昵称不能为空'
    return
  }
  saving.value = true
  editError.value = ''
  try {
    await request({
      method: 'PUT',
      url: '/profile/me',
      data: { display_name: editName.value.trim(), bio: editBio.value.trim() },
    })
    await auth.fetchMe()
    showEdit.value = false
  } catch (e) {
    editError.value = e instanceof Error ? e.message : '保存失败'
  } finally {
    saving.value = false
  }
}

onMounted(loadPhotos)
</script>

<template>
  <div class="max-w-6xl mx-auto px-4 py-10">
    <!-- 资料卡 -->
    <div class="glass-card p-8">
      <div class="flex flex-col sm:flex-row items-center gap-6">
        <UserAvatar :name="profile?.displayName ?? '?'" :size="84" />
        <div class="text-center sm:text-left flex-1">
          <div class="flex items-center justify-center sm:justify-start gap-3">
            <h1 class="text-2xl font-bold text-ink">{{ profile?.displayName }}</h1>
            <span class="text-xs font-medium text-primary-700 bg-primary-100 rounded-full px-2.5 py-0.5">@{{ profile?.username }}</span>
          </div>
          <p class="mt-2 text-sub text-sm max-w-md">{{ profile?.bio }}</p>
        </div>
        <button v-if="isSelf" class="btn-ghost !px-5 !py-2" @click="openEdit">编辑资料</button>
      </div>
    </div>

    <!-- 自己的视角：私有相册 -->
    <template v-if="isSelf">
      <div class="mt-10 flex items-center justify-between">
        <h2 class="text-lg font-semibold text-ink">我的私有相册</h2>
        <button class="btn-primary !px-4 !py-2 text-sm" @click="openUpload">上传图片</button>
      </div>

      <div v-if="loading" class="mt-4 text-center text-sub py-10">加载中…</div>
      <div v-else-if="loadError" class="mt-4 glass-card p-8 text-center text-blush">{{ loadError }}</div>
      <div v-else-if="!photos.length" class="mt-4 glass-card p-10 text-center">
        <div class="text-4xl">🔒</div>
        <p class="mt-3 text-ink font-medium">还没有私有图片</p>
        <p class="mt-1 text-sm text-sub">上传的照片只有你自己能看到</p>
        <button class="btn-ghost mt-5 !px-5 !py-2" @click="openUpload">上传第一张图片</button>
      </div>

      <div v-else class="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
        <div v-for="p in photos" :key="p.id" class="glass-card p-2 group relative">
          <div class="rounded-xl overflow-hidden cursor-pointer" @click="openPreview(p)">
            <ImagePlaceholder :title="p.title ?? '图片'" :src="p.thumb_url" aspect="1/1" />
          </div>
          <div class="px-2 py-2">
            <div class="flex items-center gap-2">
              <p class="text-sm text-ink truncate flex-1">{{ p.title ?? '未命名' }}</p>
              <button
                class="text-faint hover:text-blush shrink-0 opacity-0 group-hover:opacity-100 transition disabled:opacity-50"
                title="删除"
                :disabled="deletingId === p.id"
                @click="deletePhoto(p)"
              >
                {{ deletingId === p.id ? '…' : '🗑' }}
              </button>
            </div>
            <div class="mt-1.5 flex items-center gap-1.5">
              <span class="text-xs text-faint">{{ (p.created_at || '').slice(0, 10) }}</span>
              <span v-if="p.description && p.description !== p.title" class="text-xs text-sub truncate">{{ p.description }}</span>
            </div>
          </div>
          <span v-if="p.processing_status === 'pending' || p.processing_status === 'processing'" class="absolute top-3 right-3 text-[10px] bg-ink/60 text-white rounded-full px-2 py-0.5">处理中</span>
        </div>
      </div>
    </template>

    <!-- 他人视角 -->
    <template v-else>
      <div class="mt-10 glass-card p-8 text-center">
        <div class="w-14 h-14 mx-auto rounded-full bg-primary-50 flex items-center justify-center text-2xl">🔒</div>
        <p class="mt-4 text-ink font-medium">私有相册不可见</p>
        <p class="mt-1 text-sm text-sub">别人看不到 TA 的私有图片</p>
      </div>
    </template>

    <!-- 上传弹窗 -->
    <Teleport to="body">
      <div v-if="showUpload" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/40 backdrop-blur-sm" @click.self="closeUpload">
        <div class="glass-card max-w-lg w-full p-8">
          <div class="flex items-center justify-between">
            <h2 class="text-xl font-bold text-ink">上传私有图片</h2>
            <button class="text-faint hover:text-ink" @click="closeUpload">✕</button>
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
            <button class="btn-ghost flex-1" :disabled="uploading" @click="closeUpload">取消</button>
            <button class="btn-primary flex-1" :disabled="uploading" @click="doUpload">
              {{ uploading ? '上传中…' : '确认上传' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 预览 lightbox（复用公共组件，与图片展示一致） -->
    <ImageLightbox
      :open="!!previewing"
      :title="previewing?.title ?? ''"
      :image-url="previewUrl"
      :description="previewing?.description ?? null"
      :loading="previewLoading"
      @close="closePreview"
    >
      <template #meta>
        <p class="mt-4 text-xs text-faint">上传于 {{ (previewing?.created_at || '').slice(0, 10) }} · 仅自己可见</p>
      </template>
      <template #actions>
        <div class="flex gap-3">
          <button class="btn-ghost flex-1" @click="deleteFromPreview">删除</button>
          <button class="btn-primary flex-1" @click="downloadCurrent">下载原图</button>
        </div>
      </template>
    </ImageLightbox>

    <!-- 编辑资料弹窗 -->
    <Teleport to="body">
      <div v-if="showEdit" class="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4" @click.self="showEdit = false">
        <div class="glass-card p-6 w-full max-w-md">
          <h2 class="text-lg font-bold text-ink">编辑资料</h2>
          <div v-if="editError" class="mt-3 text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{{ editError }}</div>
          <div class="mt-4 space-y-4">
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
            <button class="btn-ghost flex-1" :disabled="saving" @click="showEdit = false">取消</button>
            <button class="btn-primary flex-1" :disabled="saving" @click="saveProfile">
              {{ saving ? '保存中…' : '保存' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>