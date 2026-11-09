<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ImagePlaceholder from '@/components/ImagePlaceholder.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import { galleryImages, tags } from '@/api/mock'
import { useAuthStore } from '@/stores/auth'
import type { GalleryImage } from '@/types'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const activeTag = ref('全部')
const search = ref('')

const filtered = computed(() => {
  let list = galleryImages
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

// 上传弹窗（响应 ?upload=1 或角色按钮）
const showUpload = ref(route.query.upload === '1')
function openUpload() {
  showUpload.value = true
}
function closeUpload() {
  showUpload.value = false
  if (route.query.upload) router.replace({ query: {} })
}

// 上传表单
const uploadTitle = ref('')
const uploadTags = ref('')
const uploaded = ref(false)
function submitUpload() {
  uploaded.value = true
  setTimeout(() => {
    showUpload.value = false
    uploaded.value = false
    uploadTitle.value = ''
    uploadTags.value = ''
  }, 1200)
}
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
        v-for="t in tags"
        :key="t"
        class="px-4 py-1.5 rounded-full text-sm transition"
        :class="activeTag === t ? 'bg-primary text-white shadow-glow' : 'bg-white/70 text-sub hover:bg-primary-50 border border-white/60'"
        @click="activeTag = t"
      >
        {{ t }}
      </button>
      <input v-model="search" class="input !w-56 ml-auto" placeholder="搜索标题 / 拍摄者 / 标签" />
    </div>

    <!-- 瀑布流 -->
    <div class="mt-8 columns-1 sm:columns-2 lg:columns-3 gap-4 space-y-4">
      <div v-for="img in filtered" :key="img.id" class="break-inside-avoid glass-card p-2 cursor-pointer hover:shadow-soft transition group" @click="openDetail(img)">
        <div class="rounded-xl overflow-hidden">
          <ImagePlaceholder :title="img.title" :aspect="img.height > img.width ? '3/4' : '4/3'" />
        </div>
        <div class="px-2 py-2.5 flex items-center gap-2">
          <UserAvatar :name="img.photographer" :size="26" />
          <span class="text-sm text-ink truncate flex-1">{{ img.title }}</span>
          <span class="text-xs text-faint shrink-0">{{ img.tags[0] }}</span>
        </div>
      </div>
    </div>

    <!-- 详情弹窗 -->
    <Teleport to="body">
      <div v-if="selected" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/40 backdrop-blur-sm" @click.self="closeDetail">
        <div class="glass-card max-w-4xl w-full overflow-hidden max-h-[90vh] flex flex-col md:flex-row">
          <div class="md:w-3/5 bg-white/30 flex items-center justify-center">
            <ImagePlaceholder :title="selected.title" aspect="4/3" />
          </div>
          <div class="md:w-2/5 p-6 flex flex-col">
            <div class="flex items-start justify-between">
              <h2 class="text-xl font-bold text-ink">{{ selected.title }}</h2>
              <button class="text-faint hover:text-ink" @click="closeDetail">✕</button>
            </div>
            <div class="mt-4 flex items-center gap-2">
              <UserAvatar :name="selected.photographer" :size="32" />
              <div>
                <p class="text-sm text-ink">{{ selected.photographer }}</p>
                <p class="text-xs text-faint">上传于 {{ selected.uploadedAt }}</p>
              </div>
            </div>
            <div class="mt-4 flex flex-wrap gap-2">
              <span v-for="t in selected.tags" :key="t" class="text-xs text-primary-700 bg-primary-50 rounded-full px-3 py-1">{{ t }}</span>
            </div>
            <p class="mt-4 text-sm text-sub leading-relaxed flex-1">
              这张照片还没有描述。摄影师用心记录下了此刻，希望你喜欢。
            </p>
            <div class="mt-6 flex gap-3">
              <button v-if="auth.isLoggedIn" class="btn-primary flex-1">下载原图</button>
              <button v-else class="btn-ghost flex-1" @click="router.push('/login')">登录后下载</button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 上传弹窗 -->
    <Teleport to="body">
      <div v-if="showUpload" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/40 backdrop-blur-sm" @click.self="closeUpload">
        <div class="glass-card max-w-lg w-full p-8">
          <div class="flex items-center justify-between">
            <h2 class="text-xl font-bold text-ink">上传图片</h2>
            <button class="text-faint hover:text-ink" @click="closeUpload">✕</button>
          </div>

          <div v-if="!uploaded">
            <!-- 拖拽区 -->
            <div class="mt-6 border-2 border-dashed border-primary-200 rounded-xl2 p-10 text-center hover:border-primary-400 transition cursor-pointer">
              <div class="w-12 h-12 mx-auto rounded-full bg-primary-50 flex items-center justify-center text-2xl text-primary">＋</div>
              <p class="mt-3 text-sm text-sub">拖拽图片到这里，或点击选择</p>
              <p class="mt-1 text-xs text-faint">支持多张、支持 JPG / PNG / WebP</p>
            </div>

            <div class="mt-6 space-y-4">
              <div>
                <label class="label">描述</label>
                <input v-model="uploadTitle" class="input" placeholder="给这张照片写点描述" />
              </div>
              <div>
                <label class="label">标签</label>
                <input v-model="uploadTags" class="input" placeholder="用逗号分隔，例如：日常, 校园" />
              </div>
            </div>

            <div class="mt-8 flex gap-3">
              <button class="btn-ghost flex-1" @click="closeUpload">取消</button>
              <button class="btn-primary flex-1" @click="submitUpload">确认上传</button>
            </div>
          </div>

          <div v-else class="py-16 text-center">
            <div class="w-14 h-14 mx-auto rounded-full bg-primary-50 flex items-center justify-center text-2xl text-primary">✓</div>
            <p class="mt-4 text-ink font-medium">上传成功，已进入审核队列</p>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>