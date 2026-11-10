<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import ImagePlaceholder from '@/components/ImagePlaceholder.vue'
import ImageLightbox from '@/components/ImageLightbox.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import { getPublishedAnnouncements } from '@/api/site'
import { request } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useDialog } from '@/composables/useDialog'
import type { AnnouncementRecord, GalleryImage } from '@/types'

const { showToast } = useDialog()

const router = useRouter()
const auth = useAuthStore()

const announcements = ref<AnnouncementRecord[]>([])
const featuredImages = ref<GalleryImage[]>([])

onMounted(async () => {
  try {
    const data = await getPublishedAnnouncements()
    announcements.value = data.items.slice(0, 3)
  } catch {
    // 静默失败，保持空列表
  }
  try {
    const data = await request<{ items: GalleryImage[] }>({ method: 'GET', url: '/images/' })
    featuredImages.value = data.items.slice(0, 6)
  } catch {
    // 静默失败
  }
})

function fmtDate(iso: string | null) {
  return iso ? iso.slice(0, 10) : ''
}

// 详情弹窗（与 Gallery 一致）
const selected = ref<GalleryImage | null>(null)
function openDetail(img: GalleryImage) {
  selected.value = img
}
function closeDetail() {
  selected.value = null
}

async function downloadSelected() {
  if (!selected.value) return
  try {
    const data = await request<{ url: string }>({ method: 'GET', url: `/images/${selected.value.id}/download` })
    window.open(data.url, '_blank')
  } catch (e) {
    showToast(e instanceof Error ? e.message : '下载失败')
  }
}
</script>

<template>
  <div>
    <!-- Hero -->
    <section class="hero-gradient-animated text-white">
      <div class="max-w-6xl mx-auto px-4 py-20 md:py-28 text-center relative overflow-hidden">
        <!-- 装饰光斑 -->
        <div class="absolute top-10 left-10 w-40 h-40 rounded-full bg-white/10 blur-3xl"></div>
        <div class="absolute bottom-6 right-16 w-56 h-56 rounded-full bg-white/10 blur-3xl"></div>

        <div class="relative">
          <span class="inline-flex items-center gap-2 text-xs font-medium bg-white/20 backdrop-blur rounded-full px-4 py-1.5 mb-6">
            浙江理工大学 · Furry 同好社团
          </span>
          <h1 class="text-4xl md:text-6xl font-bold tracking-tight leading-tight">
            毛茸茸的相遇<br />从这所学校开始
          </h1>
          <p class="mt-5 text-base md:text-lg text-white/85 max-w-xl mx-auto">
            这里是浙江理工福瑞圈。分享照片、交到同好、还能用课表工具约上一起玩的时间。
          </p>
          <div class="mt-8 flex justify-center gap-4">
            <RouterLink v-if="!auth.isLoggedIn" to="/register" class="inline-flex items-center gap-2 rounded-full bg-primary/20 backdrop-blur-md border border-white/30 text-white px-8 py-3 font-medium hover:bg-primary/30 transition">
              加入我们
            </RouterLink>
            <RouterLink to="/about" class="inline-flex items-center gap-2 rounded-full bg-white/10 border border-white/20 text-white px-8 py-3 font-medium hover:bg-white/20 transition">
              了解更多
            </RouterLink>
          </div>
        </div>
      </div>
    </section>

    <!-- 社团简介 -->
    <section class="max-w-6xl mx-auto px-4 mt-16">
      <div class="glass-card p-8 md:p-12 grid md:grid-cols-2 gap-8 items-center">
        <div>
          <h2 class="text-2xl md:text-3xl font-bold text-ink">我们是谁？</h2>
          <p class="mt-4 text-sub leading-relaxed">
            一群在浙江理工大学里喜欢毛茸茸、喜欢创作与分享的伙伴。我们组织观影、漫展、聚会，
            也用心记录校园里的每一个温暖瞬间。
          </p>
          <p class="mt-3 text-sub leading-relaxed">
            不管你是画画、摄影、写文，还是只想认识同好，这里都有你的位置。
          </p>
          <RouterLink to="/about" class="mt-6 inline-flex items-center gap-1.5 text-sm font-medium text-primary-700 bg-primary/10 border border-primary/20 hover:bg-primary/20 rounded-full px-5 py-2 transition">
            了解我们的故事 →
          </RouterLink>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <ImagePlaceholder title="社团活动" aspect="4/5" />
          <ImagePlaceholder title="日常记录" aspect="4/5" />
        </div>
      </div>
    </section>

    <!-- 最新公告 -->
    <section class="max-w-6xl mx-auto px-4 mt-16">
      <div class="flex items-center justify-between mb-6">
        <h2 class="text-xl md:text-2xl font-bold text-ink">最新公告</h2>
        <RouterLink to="/events" class="text-sm font-medium text-primary-700 bg-primary/10 border border-primary/20 hover:bg-primary/20 rounded-full px-5 py-2 transition">查看全部</RouterLink>
      </div>
      <div class="grid md:grid-cols-3 gap-4">
        <article v-for="a in announcements" :key="a.id" class="glass-card p-6 hover:shadow-soft transition">
          <div class="flex items-center gap-2">
            <span v-if="a.is_pinned" class="text-xs font-medium text-primary-700 bg-primary-100 rounded-full px-2.5 py-0.5">置顶</span>
            <span class="text-xs text-faint">{{ fmtDate(a.published_at) }}</span>
          </div>
          <h3 class="mt-3 font-semibold text-ink leading-snug">{{ a.title }}</h3>
          <p class="mt-2 text-sm text-sub leading-relaxed">{{ a.content }}</p>
        </article>
      </div>
    </section>

    <!-- 精选图片 -->
    <section class="max-w-6xl mx-auto px-4 mt-16">
      <div class="flex items-center justify-between mb-6">
        <h2 class="text-xl md:text-2xl font-bold text-ink">精选图片</h2>
        <RouterLink to="/gallery" class="text-sm font-medium text-primary-700 bg-primary/10 border border-primary/20 hover:bg-primary/20 rounded-full px-5 py-2 transition">进入图片展示 →</RouterLink>
      </div>
      <div class="grid grid-cols-2 md:grid-cols-3 gap-3 md:gap-4">
        <div v-for="img in featuredImages" :key="img.id" class="glass-card p-2 cursor-pointer hover:shadow-soft transition group" @click="openDetail(img)">
          <div class="rounded-xl overflow-hidden">
            <ImagePlaceholder :title="img.description || img.title" :src="img.thumb_url || img.display_url || img.url" :aspect="'4/3'" />
          </div>
          <div class="px-2 py-2.5">
            <div class="flex items-center gap-2">
              <UserAvatar :name="img.photographer" :size="24" />
              <span class="text-xs text-sub truncate flex-1">{{ img.description || img.title }}</span>
            </div>
            <div v-if="img.tags && img.tags.length" class="mt-1.5 flex flex-wrap gap-1.5">
              <span v-for="t in img.tags.slice(0, 3)" :key="t" class="text-xs text-primary-700 bg-primary-50 rounded-full px-2 py-0.5">{{ t }}</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 详情弹窗（与 Gallery 一致） -->
    <ImageLightbox
      :open="!!selected"
      :title="selected?.description || selected?.title || ''"
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
  </div>
</template>