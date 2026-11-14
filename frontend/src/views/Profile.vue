<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import UserAvatar from '@/components/UserAvatar.vue'
import ImagePlaceholder from '@/components/ImagePlaceholder.vue'
import ImageLightbox from '@/components/ImageLightbox.vue'
import UploadPrivateDialog from '@/components/profile/UploadPrivateDialog.vue'
import EditProfileDialog from '@/components/profile/EditProfileDialog.vue'
import ProfileRenderer from '@/components/profile/ProfileRenderer.vue'
import ProfileMediaPickerDialog from '@/components/profile/ProfileMediaPickerDialog.vue'
import { getMyLayout, getProfilePage } from '@/api/profile'
import { request } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useDialog } from '@/composables/useDialog'
import type {
  ProfileBlock,
  ProfileImage,
  ProfileMedia,
  ProfileStats,
  ProfileTheme,
} from '@/types'
import { DEFAULT_THEME } from '@/components/profile/theme'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const { showToast, showConfirm } = useDialog()

const isSelf = computed(() => !route.params.username)

// ---------- 已发布的主页 ----------
const theme = ref<ProfileTheme>({ ...DEFAULT_THEME })
const blocks = ref<ProfileBlock[]>([])
const media = ref<Record<string, ProfileMedia>>({})
const stats = ref<ProfileStats>({ joined_days: 0, gallery_image_count: 0 })
const pageUser = ref<{ username: string; display_name: string; avatar_url: string | null } | null>(null)

const pageLoading = ref(false)
const pageError = ref('')
const neverPublished = ref(false)
const unpublishedHint = ref(false)

let mediaExpiresAt = 0

const backgroundUrl = computed(() => {
  const key = theme.value.background_key
  if (!key) return null
  const m = media.value[key]
  return m?.display_url ?? m?.thumb_url ?? null
})

function applyMediaExpiry(seconds: number) {
  mediaExpiresAt = seconds > 0 ? Date.now() + seconds * 1000 : 0
}

async function loadOwnPage() {
  const data = await getMyLayout()
  theme.value = { ...DEFAULT_THEME, ...data.theme }
  media.value = data.media ?? {}
  stats.value = data.stats ?? stats.value
  applyMediaExpiry(data.media_expires_in)
  // 自己的页面看到的是已发布版本；没有发布过就给出编辑引导
  blocks.value = data.published_blocks ?? []
  neverPublished.value = data.published_blocks === null
  unpublishedHint.value =
    data.published_blocks !== null &&
    JSON.stringify(data.published_blocks) !== JSON.stringify(data.draft_blocks ?? [])
}

async function loadPublicPage(username: string) {
  const data = await getProfilePage(username)
  theme.value = { ...DEFAULT_THEME, ...data.theme }
  blocks.value = data.blocks ?? []
  media.value = data.media ?? {}
  stats.value = data.stats ?? stats.value
  pageUser.value = data.user
  applyMediaExpiry(data.media_expires_in)
}

async function loadPage() {
  pageLoading.value = true
  pageError.value = ''
  neverPublished.value = false
  unpublishedHint.value = false
  try {
    if (isSelf.value) {
      await loadOwnPage()
    } else {
      await loadPublicPage(String(route.params.username))
    }
  } catch (e) {
    const msg = e instanceof Error ? e.message : '加载失败'
    // 未发布 / 已隐藏：这不是错误页，而是「这个人还没有公开主页」
    if (!isSelf.value && /未发布|不存在|not found|PROFILE_PAGE/i.test(msg)) {
      neverPublished.value = true
    } else {
      pageError.value = msg
    }
  } finally {
    pageLoading.value = false
  }
}

/** 私有图签名 URL 有有效期，回到前台且逼近过期时静默重取一次 */
function onVisibility() {
  if (document.visibilityState !== 'visible') return
  if (!mediaExpiresAt) return
  if (Date.now() < mediaExpiresAt - 60_000) return
  if (pageLoading.value) return
  void loadPage()
}

// ---------- 私有相册（仅自己） ----------
const photos = ref<ProfileImage[]>([])
const photosLoading = ref(false)
const photosError = ref('')

async function loadPhotos() {
  if (!isSelf.value) return
  photosLoading.value = true
  photosError.value = ''
  try {
    const data = await request<{ items: ProfileImage[] }>({ method: 'GET', url: '/profile/me/images' })
    photos.value = data.items
  } catch (e) {
    photosError.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    photosLoading.value = false
  }
}

const showUpload = ref(false)
const showEdit = ref(false)
const showMediaPicker = ref(false)

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
    showToast(e instanceof Error ? e.message : '打开失败')
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
    showToast(e instanceof Error ? e.message : '下载失败')
  }
}

async function deleteFromPreview() {
  if (!previewing.value) return
  const img = previewing.value
  if (!(await showConfirm(`确定删除「${img.title ?? '这张图片'}」吗？`))) return
  try {
    await request({ method: 'DELETE', url: `/profile/me/images/${img.id}` })
    closePreview()
    await refreshAll()
  } catch (e) {
    showToast(e instanceof Error ? e.message : '删除失败')
  }
}

const deletingId = ref<string | null>(null)
async function deletePhoto(img: ProfileImage) {
  if (!(await showConfirm(`确定删除「${img.title ?? '这张图片'}」吗？`))) return
  deletingId.value = img.id
  try {
    await request({ method: 'DELETE', url: `/profile/me/images/${img.id}` })
    await refreshAll()
  } catch (e) {
    showToast(e instanceof Error ? e.message : '删除失败')
  } finally {
    deletingId.value = null
  }
}

async function refreshAll() {
  await Promise.all([loadPage(), loadPhotos()])
}

// ---------- 展示信息 ----------
const displayName = computed(() => (isSelf.value ? auth.user?.displayName : pageUser.value?.display_name) ?? '')
const username = computed(() => (isSelf.value ? auth.user?.username : pageUser.value?.username) ?? '')
const bio = computed(() => (isSelf.value ? auth.user?.bio : '') ?? '')
const avatarUrl = computed(() => (isSelf.value ? auth.user?.avatar || null : pageUser.value?.avatar_url ?? null))

const hasPage = computed(() => blocks.value.length > 0)

onMounted(() => {
  void refreshAll()
  document.addEventListener('visibilitychange', onVisibility)
})

onBeforeUnmount(() => {
  document.removeEventListener('visibilitychange', onVisibility)
})

watch(
  () => route.params.username,
  () => {
    void refreshAll()
  },
)
</script>

<template>
  <div class="max-w-6xl mx-auto px-4 py-10">
    <!-- 主页头部 -->
    <div class="glass-card p-6 sm:p-8">
      <div class="flex flex-col sm:flex-row items-center gap-6">
        <UserAvatar :name="displayName || '?'" :size="84" :src="avatarUrl" />

        <div class="text-center sm:text-left flex-1 min-w-0">
          <div class="flex flex-wrap items-center justify-center sm:justify-start gap-2.5">
            <h1 class="text-2xl font-bold text-ink">{{ displayName || '加载中…' }}</h1>
            <span v-if="username" class="text-xs font-medium text-primary-700 bg-primary-100 rounded-full px-2.5 py-0.5">@{{ username }}</span>
            <span v-if="unpublishedHint" class="text-[11px] text-blush bg-blush/10 rounded-full px-2.5 py-0.5">有未发布的修改</span>
          </div>
          <p v-if="bio" class="mt-2 text-sub text-sm max-w-md whitespace-pre-wrap">{{ bio }}</p>
        </div>

        <div v-if="isSelf" class="flex flex-col sm:flex-row gap-2 shrink-0">
          <button class="btn-primary !px-5 !py-2 text-sm" @click="router.push('/profile/me/edit')">编辑主页</button>
          <button class="btn-ghost !px-5 !py-2 text-sm" @click="showEdit = true">编辑资料</button>
        </div>
      </div>
    </div>

    <!-- 主页内容 -->
    <div class="mt-6">
      <div v-if="pageLoading" class="glass-card p-12 text-center text-sub">主页加载中…</div>

      <div v-else-if="pageError" class="glass-card p-10 text-center">
        <p class="text-blush text-sm">{{ pageError }}</p>
        <button class="btn-ghost mt-4 !px-4 !py-2 text-sm" @click="refreshAll">重试</button>
      </div>

      <div v-else-if="hasPage">
        <ProfileRenderer
          :theme="theme"
          :blocks="blocks"
          :media="media"
          :stats="stats"
          :background-url="backgroundUrl"
        />
      </div>

      <!-- 空状态：自己 vs 他人 -->
      <div v-else-if="isSelf" class="glass-card p-12 text-center">
        <div class="text-4xl">🎨</div>
        <p class="mt-4 text-ink font-medium">{{ neverPublished ? '还没有发布自己的主页' : '主页还是空的' }}</p>
        <p class="mt-1 text-sm text-sub">像 Steam 那样，把你喜欢的模块拼成自己的展示页</p>
        <button class="btn-primary mt-5 !px-5 !py-2 text-sm" @click="router.push('/profile/me/edit')">开始定制</button>
      </div>

      <div v-else class="glass-card p-12 text-center">
        <div class="w-14 h-14 mx-auto rounded-full bg-primary-50 flex items-center justify-center text-2xl">🔒</div>
        <p class="mt-4 text-ink font-medium">TA 还没有公开自己的主页</p>
        <p class="mt-1 text-sm text-sub">私有相册仍然只有本人可见</p>
      </div>
    </div>

    <!-- 自己的视角：私有相册 -->
    <template v-if="isSelf">
      <div class="mt-10 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 class="text-lg font-semibold text-ink">我的私有相册</h2>
          <p class="mt-1 text-xs text-faint">勾选「允许出现在公开主页」的照片，才会被访客看到</p>
        </div>
        <div class="flex gap-2">
          <button class="btn-ghost !px-4 !py-2 text-sm" @click="showMediaPicker = true">管理公开素材</button>
          <button class="btn-primary !px-4 !py-2 text-sm" @click="showUpload = true">上传图片</button>
        </div>
      </div>

      <div v-if="photosLoading" class="mt-4 text-center text-sub py-10">加载中…</div>
      <div v-else-if="photosError" class="mt-4 glass-card p-8 text-center text-blush">{{ photosError }}</div>
      <div v-else-if="!photos.length" class="mt-4 glass-card p-10 text-center">
        <div class="text-4xl">🔒</div>
        <p class="mt-3 text-ink font-medium">还没有私有图片</p>
        <p class="mt-1 text-sm text-sub">上传的照片默认只有你自己能看到</p>
        <button class="btn-ghost mt-5 !px-5 !py-2" @click="showUpload = true">上传第一张图片</button>
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

    <!-- 弹窗 -->
    <UploadPrivateDialog :show="showUpload" @close="showUpload = false" @uploaded="refreshAll" />
    <EditProfileDialog :show="showEdit" @close="showEdit = false" />
    <ProfileMediaPickerDialog :show="showMediaPicker" @close="showMediaPicker = false" @changed="refreshAll" />

    <!-- 预览 lightbox -->
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
  </div>
</template>
