<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { getPublishedPage } from '@/api/pages'
import type { PageBlock, PageSchema } from '@/types'
import ImagePlaceholder from '@/components/ImagePlaceholder.vue'

// 动态页面渲染入口：按 slug 拉取页面 Schema，使用白名单组件渲染。
// 未知组件类型直接忽略，不执行其内容。

const route = useRoute()
const slug = computed(() => route.params.slug as string)

const page = ref<PageSchema | null>(null)
const loading = ref(true)
const error = ref('')
const notFound = ref(false)

onMounted(async () => {
  try {
    const data = await getPublishedPage(slug.value)
    const schema = data.schema_json as PageSchema
    page.value = {
      slug: data.slug,
      title: schema.title ?? data.title,
      theme: schema.theme,
      blocks: Array.isArray(schema.blocks) ? schema.blocks : [],
    }
  } catch (e) {
    const msg = e instanceof Error ? e.message : ''
    if (msg.includes('不存在') || msg.includes('404')) {
      notFound.value = true
    } else {
      error.value = msg || '页面加载失败'
    }
  } finally {
    loading.value = false
  }
})

// ---------- 白名单组件渲染 ----------

const ALLOWED_TYPES = new Set([
  'hero',
  'rich_text',
  'image',
  'gallery',
  'countdown',
  'button',
  'notice',
  'event_info',
  'registration_form',
  'card',
  'divider',
])

function isAllowed(block: PageBlock): boolean {
  return ALLOWED_TYPES.has(block.type)
}

const validBlocks = computed(() =>
  (page.value?.blocks ?? []).filter(isAllowed),
)

const ignoredCount = computed(() =>
  (page.value?.blocks ?? []).length - validBlocks.value.length,
)

// ---------- 各组件提取 props 的辅助 ----------

function str(props: Record<string, unknown>, key: string, fallback = ''): string {
  const v = props[key]
  return typeof v === 'string' ? v : fallback
}

function countdownTarget(props: Record<string, unknown>): Date | null {
  const t = props.target
  if (typeof t === 'string') {
    const d = new Date(t)
    return isNaN(d.getTime()) ? null : d
  }
  return null
}

const countdownNow = ref(Date.now())

onMounted(() => {
  setInterval(() => {
    countdownNow.value = Date.now()
  }, 1000)
})

function countdownText(target: Date): string {
  const diff = target.getTime() - countdownNow.value
  if (diff <= 0) return '已开始'
  const d = Math.floor(diff / 86400000)
  const h = Math.floor((diff % 86400000) / 3600000)
  const m = Math.floor((diff % 3600000) / 60000)
  const s = Math.floor((diff % 60000) / 1000)
  return `${d}天 ${h}小时 ${m}分 ${s}秒`
}
</script>

<template>
  <div class="max-w-4xl mx-auto px-4 py-10">
    <!-- 加载 -->
    <div v-if="loading" class="glass-card p-12 text-center">
      <div class="w-8 h-8 border-4 border-primary-200 border-t-primary rounded-full animate-spin mx-auto"></div>
      <p class="mt-3 text-sm text-sub">加载中…</p>
    </div>

    <!-- 404 -->
    <div v-else-if="notFound" class="glass-card p-12 text-center">
      <div class="text-4xl">🔍</div>
      <p class="mt-3 text-ink font-medium text-lg">页面不存在</p>
      <p class="mt-1 text-sm text-sub">该页面可能尚未发布或已下线。</p>
    </div>

    <!-- 错误 -->
    <div v-else-if="error" class="glass-card p-12 text-center">
      <div class="text-4xl">⚠️</div>
      <p class="mt-3 text-red-600 font-medium">{{ error }}</p>
    </div>

    <!-- 渲染 -->
    <template v-else-if="page">
      <p v-if="ignoredCount > 0" class="mb-4 text-xs text-faint">
        {{ ignoredCount }} 个未知组件已被忽略
      </p>

      <template v-for="(block, i) in validBlocks" :key="i">
        <!-- Hero 横幅 -->
        <section
          v-if="block.type === 'hero'"
          class="rounded-2xl overflow-hidden mb-8"
          :style="{
            background: str(block.props, 'background', 'linear-gradient(135deg, #6B5CE7, #A78BFA)'),
          }"
        >
          <div class="px-8 py-16 text-center text-white">
            <h1 class="text-3xl md:text-5xl font-bold tracking-tight">
              {{ str(block.props, 'title', page.title ?? '活动页面') }}
            </h1>
            <p v-if="str(block.props, 'subtitle')" class="mt-4 text-lg text-white/85 max-w-xl mx-auto">
              {{ str(block.props, 'subtitle') }}
            </p>
            <img
              v-if="str(block.props, 'image')"
              :src="str(block.props, 'image')"
              :alt="str(block.props, 'title', '')"
              class="mt-8 mx-auto max-h-64 rounded-xl object-cover"
            />
          </div>
        </section>

        <!-- 富文本 -->
        <section v-else-if="block.type === 'rich_text'" class="glass-card p-8 mb-6">
          <div class="prose prose-neutral max-w-none whitespace-pre-wrap text-sub leading-relaxed">
            {{ str(block.props, 'content') }}
          </div>
        </section>

        <!-- 图片 -->
        <section v-else-if="block.type === 'image'" class="mb-6">
          <div class="glass-card p-3">
            <img
              v-if="str(block.props, 'src')"
              :src="str(block.props, 'src')"
              :alt="str(block.props, 'alt', '')"
              class="w-full rounded-xl object-cover"
            />
            <ImagePlaceholder
              v-else
              :title="str(block.props, 'alt', '图片')"
              aspect="16/9"
            />
            <p v-if="str(block.props, 'caption')" class="mt-2 text-xs text-faint text-center">
              {{ str(block.props, 'caption') }}
            </p>
          </div>
        </section>

        <!-- 倒计时 -->
        <section v-else-if="block.type === 'countdown'" class="glass-card p-8 mb-6 text-center">
          <p class="text-sm text-sub">{{ str(block.props, 'label', '距离活动开始') }}</p>
          <p class="mt-2 text-3xl md:text-4xl font-bold text-primary">
            <template v-if="countdownTarget(block.props)">
              {{ countdownText(countdownTarget(block.props)!) }}
            </template>
            <template v-else>—</template>
          </p>
        </section>

        <!-- 按钮 -->
        <section v-else-if="block.type === 'button'" class="text-center mb-6">
          <a
            :href="str(block.props, 'url', '#')"
            class="btn-primary inline-flex items-center gap-2 !px-8 !py-3 text-base"
          >
            {{ str(block.props, 'label', '点击') }}
          </a>
        </section>

        <!-- 公告 -->
        <section v-else-if="block.type === 'notice'" class="glass-card p-6 mb-6 border-l-4 border-amber-400">
          <div class="flex items-start gap-3">
            <span class="text-xl">📢</span>
            <div>
              <p class="font-semibold text-ink">{{ str(block.props, 'title', '公告') }}</p>
              <p class="mt-1 text-sm text-sub leading-relaxed">{{ str(block.props, 'content') }}</p>
            </div>
          </div>
        </section>

        <!-- 活动信息卡片 -->
        <section v-else-if="block.type === 'event_info'" class="glass-card p-6 mb-6">
          <h3 class="font-semibold text-ink mb-3">活动信息</h3>
          <div class="space-y-2 text-sm">
            <p v-if="str(block.props, 'date')" class="flex items-center gap-2 text-sub">
              <span class="text-faint">🕐</span>{{ str(block.props, 'date') }}
            </p>
            <p v-if="str(block.props, 'location')" class="flex items-center gap-2 text-sub">
              <span class="text-faint">📍</span>{{ str(block.props, 'location') }}
            </p>
            <p v-if="str(block.props, 'organizer')" class="flex items-center gap-2 text-sub">
              <span class="text-faint">👤</span>{{ str(block.props, 'organizer') }}
            </p>
          </div>
        </section>

        <!-- 卡片 -->
        <section v-else-if="block.type === 'card'" class="glass-card p-6 mb-6">
          <h3 v-if="str(block.props, 'title')" class="font-semibold text-ink">
            {{ str(block.props, 'title') }}
          </h3>
          <p v-if="str(block.props, 'content')" class="mt-2 text-sm text-sub leading-relaxed">
            {{ str(block.props, 'content') }}
          </p>
        </section>

        <!-- 分隔线 -->
        <hr v-else-if="block.type === 'divider'" class="my-8 border-primary-100" />
      </template>
    </template>
  </div>
</template>
