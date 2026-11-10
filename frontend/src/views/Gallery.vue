<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ImagePlaceholder from '@/components/ImagePlaceholder.vue'
import ImageLightbox from '@/components/ImageLightbox.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import UploadImageDialog from '@/components/gallery/UploadImageDialog.vue'
import { request } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useDialog } from '@/composables/useDialog'
import type { GalleryImage } from '@/types'

const { showToast } = useDialog()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const images = ref<GalleryImage[]>([])
const loading = ref(false)
const loadError = ref('')

const activeTag = ref('全部')
const search = ref('')

const allTags = computed(() => {
  const set = new Set<string>()
  for (const img of images.value) {
    for (const t of img.tags) set.add(t)
  }
  return ['全部', ...Array.from(set).sort()]
})

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

const selected = ref<GalleryImage | null>(null)

async function downloadSelected() {
  if (!selected.value) return
  try {
    const data = await request<{ url: string }>({ method: 'GET', url: `/images/${selected.value.id}/download` })
    window.open(data.url, '_blank')
  } catch (e) {
    showToast(e instanceof Error ? e.message : '下载失败')
  }
}

// 上传弹窗
const showUpload = ref(route.query.upload === '1')

watch(() => route.query.upload, (val) => {
  if (val === '1') showUpload.value = true
})

function closeUpload() {
  showUpload.value = false
  if (route.query.upload) router.replace({ query: {} })
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
      <button v-if="auth.isPhotographer" class="btn-primary" @click="showUpload = true">上传图片</button>
    </div>

    <!-- 筛选栏 -->
    <div class="mt-8 flex flex-wrap items-center gap-3">
      <button
        v-for="t in allTags"
        :key="t"
        class="text-sm font-medium text-primary-700 rounded-full px-5 py-2 transition"
        :class="activeTag === t ? 'bg-primary/30 border border-primary/30 shadow-glass text-primary-800' : 'bg-primary/5 border border-primary/10 hover:bg-primary/15'"
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
      <div v-for="img in filtered" :key="img.id" class="break-inside-avoid glass-card p-2 cursor-pointer hover:shadow-soft transition group" @click="selected = img">
        <div class="rounded-xl overflow-hidden">
          <ImagePlaceholder :title="img.description || img.title" :src="img.thumb_url || img.url" :aspect="img.height && img.width && img.height > img.width ? '3/4' : '4/3'" />
        </div>
        <div class="px-2 py-2.5">
          <div class="flex items-center gap-2">
            <UserAvatar :name="img.photographer" :size="26" />
            <span class="text-sm text-ink truncate flex-1">{{ img.description || img.title }}</span>
          </div>
          <div v-if="img.tags && img.tags.length" class="mt-1.5 flex flex-wrap gap-1.5">
            <span v-for="t in img.tags.slice(0, 3)" :key="t" class="tag-badge">{{ t }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 详情弹窗 -->
    <ImageLightbox
      :open="!!selected"
      :title="selected?.description || selected?.title || ''"
      :image-url="selected ? (selected.display_url || selected.url) : null"
      :description="selected?.description ?? null"
      @close="selected = null"
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
          <span v-for="t in selected?.tags ?? []" :key="t" class="tag-badge-lg">{{ t }}</span>
        </div>
      </template>
      <template #actions>
        <button v-if="auth.isLoggedIn" class="btn-primary w-full" @click="downloadSelected">下载原图</button>
        <button v-else class="btn-ghost w-full" @click="router.push('/login')">登录后下载</button>
      </template>
    </ImageLightbox>

    <!-- 上传弹窗 -->
    <UploadImageDialog
      :show="showUpload"
      @close="closeUpload"
      @uploaded="loadImages"
    />
  </div>
</template>
