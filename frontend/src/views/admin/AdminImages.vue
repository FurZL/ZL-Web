<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import ImagePlaceholder from '@/components/ImagePlaceholder.vue'
import ImageLightbox from '@/components/ImageLightbox.vue'
import {
  adminDeleteImage,
  adminGetImageStats,
  adminListImages,
  adminSetImageModeration,
  adminSetImageTags,
  adminSetImageVisibility,
} from '@/api/adminImages'
import type { AdminImageStats, GalleryImage } from '@/types'

const images = ref<GalleryImage[]>([])
const stats = ref<AdminImageStats | null>(null)
const loading = ref(true)
const error = ref('')
const acting = ref<string | null>(null)

// 分页
const page = ref(1)
const pageSize = 20
const total = ref(0)

// 筛选
const activeTab = ref<'all' | 'pending' | 'approved' | 'rejected'>('all')
const publicFilter = ref<boolean | null>(null)

// 标签编辑弹窗
const editingTags = ref<GalleryImage | null>(null)
const tagInput = ref('')

// 详情弹窗
const selected = ref<GalleryImage | null>(null)

const statusMap: Record<string, { text: string; cls: string }> = {
  pending: { text: '待审核', cls: 'bg-amber-100 text-amber-700' },
  approved: { text: '已通过', cls: 'bg-emerald-100 text-emerald-700' },
  rejected: { text: '已拒绝', cls: 'bg-red-100 text-red-600' },
}

const tabs = [
  { key: 'all', label: '全部' },
  { key: 'pending', label: '待审核' },
  { key: 'approved', label: '已通过' },
  { key: 'rejected', label: '已拒绝' },
] as const

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [imgData, statData] = await Promise.all([
      adminListImages({
        page: page.value,
        page_size: pageSize,
        status: activeTab.value === 'all' ? null : activeTab.value,
        is_public: publicFilter.value,
      }),
      adminGetImageStats(),
    ])
    images.value = imgData.items
    total.value = imgData.pagination.total
    stats.value = statData
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)

function switchTab(tab: string) {
  activeTab.value = tab as typeof activeTab.value
  page.value = 1
  load()
}

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

function goPage(p: number) {
  if (p < 1 || p > totalPages.value) return
  page.value = p
  load()
}

// 审核
async function approve(img: GalleryImage) {
  acting.value = img.id
  try {
    await adminSetImageModeration(img.id, 'approved')
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '操作失败'
  } finally {
    acting.value = null
  }
}

async function reject(img: GalleryImage) {
  acting.value = img.id
  try {
    await adminSetImageModeration(img.id, 'rejected')
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '操作失败'
  } finally {
    acting.value = null
  }
}

// 公开/私有
async function toggleVisibility(img: GalleryImage) {
  acting.value = img.id
  try {
    await adminSetImageVisibility(img.id, !img.is_public)
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '操作失败'
  } finally {
    acting.value = null
  }
}

// 删除
async function remove(img: GalleryImage) {
  if (!confirm(`确定删除「${img.description || img.title}」吗？此操作不可恢复。`)) return
  acting.value = img.id
  try {
    await adminDeleteImage(img.id)
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '删除失败'
  } finally {
    acting.value = null
  }
}

// 标签编辑
function openTagEditor(img: GalleryImage) {
  editingTags.value = img
  tagInput.value = img.tags.join(', ')
}

async function saveTags() {
  if (!editingTags.value) return
  acting.value = editingTags.value.id
  try {
    const tags = tagInput.value.split(/[,，]/).map((t) => t.trim()).filter(Boolean)
    await adminSetImageTags(editingTags.value.id, tags)
    editingTags.value = null
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '保存失败'
  } finally {
    acting.value = null
  }
}

function fmtDate(iso: string | null) {
  return iso ? new Date(iso).toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'
}
</script>

<template>
  <div>
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-ink">图片管理</h1>
        <p class="mt-1 text-sm text-sub">管理公开图片、审核、标签与删除</p>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div v-if="stats" class="mt-6 grid grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="glass-card p-5">
        <p class="text-xs text-faint">总图片</p>
        <p class="mt-2 text-2xl font-bold text-ink">{{ stats.total }}</p>
      </div>
      <div class="glass-card p-5">
        <p class="text-xs text-faint">待审核</p>
        <p class="mt-2 text-2xl font-bold text-amber-600">{{ stats.pending }}</p>
      </div>
      <div class="glass-card p-5">
        <p class="text-xs text-faint">已通过</p>
        <p class="mt-2 text-2xl font-bold text-emerald-600">{{ stats.approved }}</p>
      </div>
      <div class="glass-card p-5">
        <p class="text-xs text-faint">已拒绝</p>
        <p class="mt-2 text-2xl font-bold text-red-500">{{ stats.rejected }}</p>
      </div>
    </div>

    <!-- 筛选 Tab -->
    <div class="mt-6 flex flex-wrap items-center gap-2">
      <button
        v-for="t in tabs"
        :key="t.key"
        class="text-sm font-medium text-primary-700 rounded-full px-5 py-2 transition"
        :class="activeTab === t.key ? 'bg-primary/30 border border-primary/30 shadow-glass text-primary-800' : 'bg-primary/5 border border-primary/10 hover:bg-primary/15'"
        @click="switchTab(t.key)"
      >
        {{ t.label }}
        <span v-if="t.key === 'pending' && stats?.pending" class="ml-1 text-xs bg-amber-500 text-white rounded-full px-1.5 py-0.5">{{ stats.pending }}</span>
      </button>

      <div class="ml-auto flex items-center gap-2">
        <button
          class="text-sm font-medium rounded-full px-4 py-2 transition"
          :class="publicFilter === null ? 'bg-primary/15 text-primary-700 border border-primary/20' : 'bg-primary/5 text-sub border border-primary/10 hover:bg-primary/15'"
          @click="publicFilter = null; page = 1; load()"
        >
          全部
        </button>
        <button
          class="text-sm font-medium rounded-full px-4 py-2 transition"
          :class="publicFilter === true ? 'bg-primary/15 text-primary-700 border border-primary/20' : 'bg-primary/5 text-sub border border-primary/10 hover:bg-primary/15'"
          @click="publicFilter = true; page = 1; load()"
        >
          公开
        </button>
        <button
          class="text-sm font-medium rounded-full px-4 py-2 transition"
          :class="publicFilter === false ? 'bg-primary/15 text-primary-700 border border-primary/20' : 'bg-primary/5 text-sub border border-primary/10 hover:bg-primary/15'"
          @click="publicFilter = false; page = 1; load()"
        >
          非公开
        </button>
      </div>
    </div>

    <div v-if="error" class="mt-4 text-sm text-red-600 bg-red-50 rounded-lg px-4 py-2">{{ error }}</div>

    <!-- 图片网格 -->
    <div v-if="loading" class="mt-8 glass-card p-12 text-center">
      <div class="w-8 h-8 border-4 border-primary-200 border-t-primary rounded-full animate-spin mx-auto"></div>
      <p class="mt-3 text-sm text-sub">加载中…</p>
    </div>

    <div v-else-if="images.length === 0" class="mt-8 glass-card p-12 text-center">
      <div class="text-4xl">🖼</div>
      <p class="mt-3 text-ink font-medium">暂无图片</p>
      <p class="mt-1 text-sm text-sub">切换筛选条件试试</p>
    </div>

    <div v-else class="mt-6 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
      <div v-for="img in images" :key="img.id" class="glass-card p-2">
        <!-- 缩略图 -->
        <div class="rounded-xl overflow-hidden cursor-pointer group relative" @click="selected = img">
          <ImagePlaceholder
            :title="img.description || img.title"
            :src="img.thumb_url || img.display_url || img.url"
            aspect="1/1"
          />
          <!-- 状态角标 -->
          <span
            class="absolute top-2 left-2 text-[10px] font-medium rounded-full px-2 py-0.5"
            :class="statusMap[img.moderation_status]?.cls ?? 'bg-gray-100 text-gray-600'"
          >
            {{ statusMap[img.moderation_status]?.text ?? img.moderation_status }}
          </span>
          <span v-if="!img.is_public" class="absolute top-2 right-2 text-[10px] font-medium bg-ink/60 text-white rounded-full px-2 py-0.5">
            私有
          </span>
        </div>

        <!-- 信息 -->
        <div class="px-2 py-2">
          <p class="text-sm text-ink truncate">{{ img.description || img.title }}</p>
          <p class="text-xs text-faint mt-0.5 truncate">{{ img.photographer }} · {{ fmtDate(img.uploaded_at) }}</p>
          <!-- 标签 -->
          <div v-if="img.tags.length" class="mt-1 flex flex-wrap gap-1">
            <span v-for="t in img.tags.slice(0, 3)" :key="t" class="text-[10px] text-primary-700 bg-primary-50 rounded-full px-1.5 py-0.5">{{ t }}</span>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="px-2 pb-2 flex flex-wrap gap-1.5">
          <button
            v-if="img.moderation_status !== 'approved'"
            class="text-[11px] px-2.5 py-1 rounded-lg border border-emerald-200 text-emerald-600 hover:bg-emerald-50 transition"
            :disabled="acting === img.id"
            @click="approve(img)"
          >
            通过
          </button>
          <button
            v-if="img.moderation_status !== 'rejected'"
            class="text-[11px] px-2.5 py-1 rounded-lg border border-red-200 text-red-500 hover:bg-red-50 transition"
            :disabled="acting === img.id"
            @click="reject(img)"
          >
            拒绝
          </button>
          <button
            class="text-[11px] px-2.5 py-1 rounded-lg border border-gray-200 text-faint hover:border-primary-200 transition"
            :disabled="acting === img.id"
            @click="toggleVisibility(img)"
          >
            {{ img.is_public ? '设为私有' : '设为公开' }}
          </button>
          <button
            class="text-[11px] px-2.5 py-1 rounded-lg border border-gray-200 text-faint hover:border-primary-200 transition"
            @click="openTagEditor(img)"
          >
            标签
          </button>
          <button
            class="text-[11px] px-2.5 py-1 rounded-lg border border-gray-200 text-red-500 hover:border-red-300 transition"
            :disabled="acting === img.id"
            @click="remove(img)"
          >
            删除
          </button>
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <div v-if="totalPages > 1" class="mt-6 flex items-center justify-center gap-2">
      <button class="text-sm px-4 py-2 rounded-full bg-primary/5 border border-primary/10 hover:bg-primary/15 transition" :disabled="page <= 1" @click="goPage(page - 1)">
        上一页
      </button>
      <span class="text-sm text-sub">{{ page }} / {{ totalPages }}</span>
      <button class="text-sm px-4 py-2 rounded-full bg-primary/5 border border-primary/10 hover:bg-primary/15 transition" :disabled="page >= totalPages" @click="goPage(page + 1)">
        下一页
      </button>
    </div>

    <!-- 标签编辑弹窗 -->
    <div v-if="editingTags" class="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4" @click.self="editingTags = null">
      <div class="glass-card p-6 w-full max-w-md">
        <h2 class="text-lg font-bold text-ink">编辑标签</h2>
        <p class="mt-1 text-xs text-faint">{{ editingTags.description || editingTags.title }}</p>
        <div class="mt-4">
          <label class="label">标签（逗号分隔）</label>
          <input v-model="tagInput" class="input" placeholder="例如：日常, 校园, 治愈" />
        </div>
        <div class="mt-6 flex gap-3">
          <button class="btn-ghost flex-1" @click="editingTags = null">取消</button>
          <button class="btn-primary flex-1" :disabled="acting === editingTags.id" @click="saveTags">
            {{ acting === editingTags.id ? '保存中…' : '保存' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 图片详情 -->
    <ImageLightbox
      :open="!!selected"
      :title="selected?.description || selected?.title || ''"
      :image-url="selected ? (selected.display_url || selected.url) : null"
      :description="selected?.description ?? null"
      @close="selected = null"
    >
      <template #meta>
        <div class="mt-4 flex items-center gap-2">
          <div>
            <p class="text-sm text-ink">{{ selected?.photographer }}</p>
            <p class="text-xs text-faint">上传于 {{ fmtDate(selected?.uploaded_at ?? null) }}</p>
            <div class="mt-1 flex items-center gap-2">
              <span
                class="text-xs font-medium rounded-full px-2 py-0.5"
                :class="statusMap[selected?.moderation_status ?? '']?.cls ?? 'bg-gray-100 text-gray-600'"
              >
                {{ statusMap[selected?.moderation_status ?? '']?.text ?? '' }}
              </span>
              <span class="text-xs text-faint">{{ selected?.is_public ? '公开' : '私有' }}</span>
            </div>
          </div>
        </div>
        <div class="mt-3 flex flex-wrap gap-1.5">
          <span v-for="t in selected?.tags ?? []" :key="t" class="text-xs text-primary-700 bg-primary-50 rounded-full px-2 py-0.5">{{ t }}</span>
        </div>
      </template>
    </ImageLightbox>
  </div>
</template>
