<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ImagePlaceholder from '@/components/ImagePlaceholder.vue'
import ImageLightbox from '@/components/ImageLightbox.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import { tags as mockTags } from '@/api/mock'
import { request } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import type { GalleryImage, UploadIntent } from '@/types'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const images = ref<GalleryImage[]>([])
const loading = ref(false)
const loadError = ref('')

const activeTag = ref('全部')
const search = ref('')

async function loadImages() {
  loading.value = true
  loadError.value = ''
  try {
    const data = await request<{ items: GalleryImage[]; pagination: { total: number } }>({
      method: 'GET',
      url: '/images/',
    })
    images.value = data.items
  } catch (e) {
    loadError.value = e instanceof Error ? e.message : '图片加载失败'
  } finally {
    loading.value = false
  }
}

const filtered = computed(() => {
  let list = images.value
  if (activeTag.value !== '全部') list = list.filter((i) => i.tags.includes(activeTag.value))
  if (search.value.trim()) {
    const q = search.value.trim()
    list = list.filter((i) => i.title.includes(q) || i.photographer.includes(q) || i.tags.some((t) => t.includes(q)))
  }
  return list
})

// 详情弹窗
const selected = ref<GalleryImage | null>(null)
function openDetail(img: GalleryImage) {
  selected.value = img
}
function closeDetail() {
  selected.value = null
}

async function downloadSelected() {
  if (selected.value) await downloadImage(selected.value)
}

async function downloadImage(img: GalleryImage) {
  try {
    const data = await request<{ url: string }>({ method: 'GET', url: `/images/${img.id}/download` })
    window.open(data.url, '_blank')
  } catch (e) {
    alert(e instanceof Error ? e.message : '下载失败')
  }
}

// 上传弹窗
const showUpload = ref(route.query.upload === '1')
const file = ref<File | null>(null)
const filePreview = ref('')
const uploadTitle = ref('')
const uploadTags = ref('')
const uploading = ref(false)
const uploadError = ref('')
const uploaded = ref(false)

function openUpload() {
  showUpload.value = true
}
function closeUpload() {
  if (!uploading.value) {
    showUpload.value = false
    resetUpload()
    if (route.query.upload) router.replace({ query: {} })
  }
}

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
  // 客户端预校验类型
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
    // 1. 申请上传意图
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

    // 2. 直传 COS（预签名 PUT）
    await fetch(intent.upload_url, {
      method: 'PUT',
      headers: { 'Content-Type': file.value.type || 'image/jpeg' },
      body: file.value,
    })

    // 3. 通知后端完成
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
    await loadImages()
    setTimeout(() => {
      closeUpload()
    }, 1200)
  } catch (e) {
    uploadError.value = e instanceof Error ? e.message : '上传失败，请重试'
  } finally {
    uploading.value = false
  }
}

onMounted(loadImages)
</script>

<template>
  <div class="max-w-6xl mx-auto px-4 py-10">
    <div class="flex flex-col md:flex-row md:items-end md:justify-between gap-6">
      <div>
        <h1 class="text-3xl font-bold text-ink">图片展示</h1>
        <p class="mt-2 text-sub">社团的活动照片与圈内创作，记录每一个毛茸茸的瞬间。</p>
      </div>
      <button v-if="auth.isPhotographer" class="btn-primary" @click="openUpload">上传图片</button>
    </div>

    <!-- 筛选栏 -->
    <div class="mt-8 flex flex-wrap items-center gap-3">
      <button
        v-for="t in mockTags"
        :key="t"
        class="px-4 py-1.5 rounded-full text-sm transition"
        :class="activeTag === t ? 'bg-primary text-white shadow-glow' : 'bg-white/70 text-sub hover:bg-primary-50 border border-white/60'"
        @click="activeTag = t"
      >
        {{ t }}
      </button>
      <input v-model="search" class="input !w-56 ml-auto" placeholder="搜索标题 / 拍摄者 / 标签" />
    </div>

    <!-- 加载/错误/空状态 -->
    <div v-if="loading" class="mt-10 text-center text-sub py-20">图片加载中…</div>
    <div v-else-if="loadError" class="mt-10 glass-card p-12 text-center">
      <p class="text-blush">{{ loadError }}</p>
    </div>
    <div v-else-if="!images.length" class="mt-10 glass-card p-16 text-center">
      <div class="text-5xl">🖼</div>
      <p class="mt-4 text-ink font-medium">还没有公开图片</p>
      <p class="mt-1 text-sm text-sub">摄影师上传并通过审核后，照片会展示在这里</p>
    </div>

    <!-- 瀑布流 -->
    <div v-else class="mt-8 columns-1 sm:columns-2 lg:columns-3 gap-4 space-y-4">
      <div v-for="img in filtered" :key="img.id" class="break-inside-avoid glass-card p-2 cursor-pointer hover:shadow-soft transition group" @click="openDetail(img)">
        <div class="rounded-xl overflow-hidden">
          <ImagePlaceholder :title="img.title" :src="img.thumb_url || img.url" :aspect="img.height && img.width && img.height > img.width ? '3/4' : '4/3'" />
        </div>
        <div class="px-2 py-2.5 flex items-center gap-2">
          <UserAvatar :name="img.photographer" :size="26" />
          <span class="text-sm text-ink truncate flex-1">{{ img.title }}</span>
          <span v-if="img.tags[0]" class="text-xs text-faint shrink-0">{{ img.tags[0] }}</span>
        </div>
      </div>
    </div>

    <!-- 详情弹窗（复用公共组件） -->
    <ImageLightbox
      :open="!!selected"
      :title="selected?.title ?? ''"
      :image-url="selected ? (selected.display_url || selected.url) : null"
      :description="selected?.description ?? null"
      @close="closeDetail"
    >
      <template #meta>
        <div class="mt-4 flex items-center gap-2">
          <UserAvatar :name="selected?.photographer ?? ''" :size="32" />
          <div>
            <p class="text-sm text-ink">{{ selected?.photographer }}</p>
            <p class="text-xs text-faint">上传于 {{ (selected?.uploaded_at || '').slice(0, 10) }}</p>
          </div>
        </div>
        <div class="mt-4 flex flex-wrap gap-2">
          <span v-for="t in selected?.tags ?? []" :key="t" class="text-xs text-primary-700 bg-primary-50 rounded-full px-3 py-1">{{ t }}</span>
        </div>
      </template>
      <template #actions>
        <button v-if="auth.isLoggedIn" class="btn-primary w-full" @click="downloadSelected">下载原图</button>
        <button v-else class="btn-ghost w-full" @click="router.push('/login')">登录后下载</button>
      </template>
    </ImageLightbox>

    <!-- 上传弹窗 -->
    <Teleport to="body">
      <div v-if="showUpload" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/40 backdrop-blur-sm" @click.self="closeUpload">
        <div class="glass-card max-w-lg w-full p-8">
          <div class="flex items-center justify-between">
            <h2 class="text-xl font-bold text-ink">上传图片</h2>
            <button class="text-faint hover:text-ink" @click="closeUpload">✕</button>
          </div>

          <div v-if="!uploaded">
            <!-- 文件选择 -->
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
              <button class="btn-ghost flex-1" :disabled="uploading" @click="closeUpload">取消</button>
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
  </div>
</template>