<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ProfileBlock, ProfileLinkItem, ProfileSpan, ProfileStatsKey } from '@/types'
import { ALLOWED_SPANS, BLOCK_LABELS, isBlockType } from '../blocks/registry'
import { STAT_LABELS, num, str, strList } from '../blocks/types'
import { useProfileLayoutStore } from '@/stores/profileLayout'
import MediaPicker from './MediaPicker.vue'

const props = defineProps<{ blockId: string | null }>()

const store = useProfileLayoutStore()

const block = computed<ProfileBlock | null>(
  () => store.blocks.find((b) => b.id === props.blockId) ?? null,
)

const type = computed(() => (block.value && isBlockType(block.value.type) ? block.value.type : null))

const spans = computed<ProfileSpan[]>(() => (type.value ? ALLOWED_SPANS[type.value] : []))

function text(key: string, fallback = ''): string {
  return block.value ? str(block.value, key, fallback) : fallback
}

function setValue(key: string, value: unknown) {
  if (block.value) store.updateProps(block.value.id, { [key]: value })
}

function setSpan(span: ProfileSpan) {
  if (block.value) store.setSpan(block.value.id, span)
}

// ---------- photo_wall ----------
const wallKeys = computed(() => (block.value ? strList(block.value, 'object_keys') : []))
const wallColumns = computed(() => (block.value ? num(block.value, 'columns', 3) : 3))

// ---------- featured_photo ----------
const featuredKey = computed(() => (block.value ? str(block.value, 'object_key') : ''))

// ---------- links ----------
const linkItems = computed<ProfileLinkItem[]>(() => {
  if (!block.value) return []
  const raw = block.value.props.items
  if (!Array.isArray(raw)) return []
  return raw
    .filter((x): x is Record<string, unknown> => typeof x === 'object' && x !== null)
    .map((x) => ({
      label: typeof x.label === 'string' ? x.label : '',
      url: typeof x.url === 'string' ? x.url : '',
    }))
})

const linksError = ref('')

function writeLinks(items: ProfileLinkItem[]) {
  setValue('items', items)
}

function addLink() {
  if (linkItems.value.length >= 8) return
  writeLinks([...linkItems.value, { label: '', url: '' }])
}

function updateLink(index: number, patch: Partial<ProfileLinkItem>) {
  const next = linkItems.value.map((it, i) => (i === index ? { ...it, ...patch } : it))
  writeLinks(next)
}

function removeLink(index: number) {
  writeLinks(linkItems.value.filter((_, i) => i !== index))
}

function linkUrlError(url: string): string {
  if (!url) return ''
  return /^https:\/\/\S+$/i.test(url) ? '' : '需以 https:// 开头'
}

// ---------- stats ----------
const statsKeys = computed<ProfileStatsKey[]>(() => {
  if (!block.value) return []
  return strList(block.value, 'items').filter(
    (k): k is ProfileStatsKey => k === 'joined_days' || k === 'gallery_image_count',
  )
})

function toggleStat(key: ProfileStatsKey) {
  const current = statsKeys.value
  if (current.includes(key)) {
    setValue('items', current.filter((k) => k !== key))
    return
  }
  if (current.length >= 2) {
    linksError.value = '最多选 2 项'
    return
  }
  linksError.value = ''
  setValue('items', [...current, key])
}

const statsChoices: ProfileStatsKey[] = ['joined_days', 'gallery_image_count']
</script>

<template>
  <div class="glass-card p-4">
    <template v-if="!block || !type">
      <h2 class="text-sm font-semibold text-ink">模块设置</h2>
      <p class="mt-3 text-xs leading-relaxed text-faint">
        在画布里点选一个模块，这里会显示它可调整的内容。
      </p>
    </template>

    <template v-else>
      <div class="flex items-baseline justify-between">
        <h2 class="text-sm font-semibold text-ink">{{ BLOCK_LABELS[type] }}</h2>
        <span class="text-[10px] text-faint font-mono">{{ block.id }}</span>
      </div>

      <!-- 宽度 -->
      <div class="mt-4">
        <label class="label !text-xs">宽度</label>
        <div class="flex flex-wrap gap-1.5">
          <button
            v-for="s in spans"
            :key="s"
            class="px-2.5 py-1 rounded-lg text-[11px] border transition"
            :class="block.span === s
              ? 'text-white border-transparent'
              : 'text-sub border-primary-100 hover:border-primary-300'"
            :style="block.span === s ? { background: 'var(--profile-primary)' } : undefined"
            :disabled="spans.length === 1"
            @click="setSpan(s)"
          >
            {{ s === 12 ? '整行' : `${s}/12` }}
          </button>
        </div>
        <p v-if="spans.length === 1" class="mt-1.5 text-[10px] text-faint">该模块固定整行</p>
      </div>

      <!-- 按类型 -->
      <div class="mt-5 space-y-4">
        <!-- bio -->
        <template v-if="type === 'bio'">
          <div>
            <label class="label !text-xs">简介内容</label>
            <textarea
              class="input min-h-[120px] resize-y"
              :value="text('text')"
              maxlength="500"
              placeholder="介绍一下自己，支持换行"
              @input="setValue('text', ($event.target as HTMLTextAreaElement).value)"
            ></textarea>
            <p class="mt-1 text-right text-[10px] text-faint">{{ text('text').length }} / 500</p>
          </div>
        </template>

        <!-- quote -->
        <template v-else-if="type === 'quote'">
          <div>
            <label class="label !text-xs">一句话</label>
            <input
              class="input"
              :value="text('text')"
              maxlength="160"
              placeholder="比如：今天也要毛茸茸的"
              @input="setValue('text', ($event.target as HTMLInputElement).value)"
            />
          </div>
          <div>
            <label class="label !text-xs">署名（可选）</label>
            <input
              class="input"
              :value="text('author')"
              maxlength="40"
              placeholder="谁说的"
              @input="setValue('author', ($event.target as HTMLInputElement).value)"
            />
          </div>
        </template>

        <!-- featured_photo -->
        <template v-else-if="type === 'featured_photo'">
          <div>
            <label class="label !text-xs">主图</label>
            <MediaPicker
              :model-value="featuredKey ? [featuredKey] : []"
              @update:model-value="setValue('object_key', $event[0] ?? '')"
            />
          </div>
          <div>
            <label class="label !text-xs">图片说明（可选）</label>
            <input
              class="input"
              :value="text('caption')"
              maxlength="80"
              placeholder="一句话说明这张图"
              @input="setValue('caption', ($event.target as HTMLInputElement).value)"
            />
          </div>
        </template>

        <!-- photo_wall -->
        <template v-else-if="type === 'photo_wall'">
          <div>
            <label class="label !text-xs">照片（{{ wallKeys.length }} / 12）</label>
            <MediaPicker
              :model-value="wallKeys"
              multiple
              :max="12"
              @update:model-value="setValue('object_keys', $event)"
            />
          </div>
          <div>
            <label class="label !text-xs">每行列数</label>
            <div class="flex gap-1.5">
              <button
                v-for="c in [2, 3]"
                :key="c"
                class="px-3 py-1 rounded-lg text-[11px] border transition"
                :class="wallColumns === c ? 'text-white border-transparent' : 'text-sub border-primary-100 hover:border-primary-300'"
                :style="wallColumns === c ? { background: 'var(--profile-primary)' } : undefined"
                @click="setValue('columns', c)"
              >{{ c }} 列</button>
            </div>
          </div>
        </template>

        <!-- gallery_link -->
        <template v-else-if="type === 'gallery_link'">
          <div>
            <label class="label !text-xs">图片标签</label>
            <input
              class="input"
              :value="text('tag')"
              maxlength="40"
              placeholder="留空表示进入全部图片"
              @input="setValue('tag', ($event.target as HTMLInputElement).value)"
            />
            <p class="mt-1 text-[10px] text-faint">点击后跳到图片展示页并按该标签筛选</p>
          </div>
          <div>
            <label class="label !text-xs">按钮文字</label>
            <input
              class="input"
              :value="text('label')"
              maxlength="20"
              placeholder="去看图"
              @input="setValue('label', ($event.target as HTMLInputElement).value)"
            />
          </div>
        </template>

        <!-- links -->
        <template v-else-if="type === 'links'">
          <div>
            <div class="flex items-center justify-between">
              <label class="label !text-xs !mb-0">链接（{{ linkItems.length }} / 8）</label>
              <button
                class="text-[11px] text-primary-700 hover:underline disabled:opacity-40"
                :disabled="linkItems.length >= 8"
                @click="addLink"
              >＋ 添加</button>
            </div>

            <div v-if="!linkItems.length" class="mt-2 rounded-xl border border-dashed border-primary-200 px-3 py-4 text-center text-[11px] text-faint">
              还没有链接
            </div>

            <div v-for="(item, i) in linkItems" :key="i" class="mt-2 rounded-xl border border-primary-100 p-2.5">
              <div class="flex items-center gap-1.5">
                <input
                  class="input !py-1.5 !text-xs"
                  :value="item.label"
                  maxlength="20"
                  placeholder="名称"
                  @input="updateLink(i, { label: ($event.target as HTMLInputElement).value })"
                />
                <button class="text-faint hover:text-blush text-xs shrink-0" title="删除" @click="removeLink(i)">✕</button>
              </div>
              <input
                class="input !py-1.5 !text-xs mt-1.5"
                :value="item.url"
                maxlength="300"
                placeholder="https://example.com"
                @input="updateLink(i, { url: ($event.target as HTMLInputElement).value })"
              />
              <p v-if="linkUrlError(item.url)" class="mt-1 text-[10px] text-blush">{{ linkUrlError(item.url) }}</p>
            </div>
          </div>
        </template>

        <!-- stats -->
        <template v-else-if="type === 'stats'">
          <div>
            <label class="label !text-xs">显示的数据（最多 2 项）</label>
            <label
              v-for="k in statsChoices"
              :key="k"
              class="flex items-center gap-2 py-1.5 cursor-pointer"
            >
              <input
                type="checkbox"
                class="accent-primary"
                :checked="statsKeys.includes(k)"
                @change="toggleStat(k)"
              />
              <span class="text-xs text-sub">{{ STAT_LABELS[k].label }}</span>
            </label>
            <p v-if="linksError" class="mt-1 text-[10px] text-blush">{{ linksError }}</p>
          </div>
        </template>

        <!-- html_block -->
        <template v-else-if="type === 'html_block'">
          <div class="rounded-xl bg-primary-50/70 p-3">
            <p class="text-[11px] leading-relaxed text-sub">
              自定义 HTML 在沙箱 iframe 中运行，读不到登录态，也不能调用本站接口。
              当前版本只支持显示，编写入口会在后续版本开放。
            </p>
          </div>
          <div>
            <label class="label !text-xs">高度</label>
            <div class="flex gap-1.5">
              <button
                v-for="h in [200, 400, 600]"
                :key="h"
                class="px-3 py-1 rounded-lg text-[11px] border transition"
                :class="num(block, 'height', 200) === h ? 'text-white border-transparent' : 'text-sub border-primary-100 hover:border-primary-300'"
                :style="num(block, 'height', 200) === h ? { background: 'var(--profile-primary)' } : undefined"
                @click="setValue('height', h)"
              >{{ h }}px</button>
            </div>
          </div>
          <p v-if="text('html')" class="text-[10px] text-faint">已包含 {{ text('html').length }} 个字符的内容</p>
        </template>
      </div>
    </template>
  </div>
</template>
