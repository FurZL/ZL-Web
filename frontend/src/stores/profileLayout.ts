/**
 * 个人主页编辑器的草稿状态。
 * 撤销/重做基于「整份快照」，因为编辑动作分散在属性面板的各个 v-model 上，
 * 逐个 action 记录历史会漏掉一半路径。快照由深层 watch + 防抖收集。
 */
import { computed, nextTick, ref, watch } from 'vue'
import { defineStore } from 'pinia'
import {
  discardMyDraft,
  getMyLayout,
  getMyMedia,
  publishMyLayout,
  saveMyLayout,
  saveMyTheme,
} from '@/api/profile'
import { DEFAULT_THEME, THEME_PRESETS } from '@/components/profile/theme'
import { newBlock } from '@/components/profile/blocks/registry'
import type {
  ProfileBlock,
  ProfileBlockType,
  ProfileMedia,
  ProfileMediaOption,
  ProfileSpan,
  ProfileStats,
  ProfileTheme,
} from '@/types'

const HISTORY_LIMIT = 50
const HISTORY_DEBOUNCE_MS = 400

interface Snapshot {
  blocks: ProfileBlock[]
  theme: ProfileTheme
}

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T
}

function serialize(blocks: ProfileBlock[], theme: ProfileTheme): string {
  return JSON.stringify({ blocks, theme })
}

const EMPTY_STATS: ProfileStats = { joined_days: 0, gallery_image_count: 0 }

export const useProfileLayoutStore = defineStore('profileLayout', () => {
  const blocks = ref<ProfileBlock[]>([])
  const theme = ref<ProfileTheme>({ ...DEFAULT_THEME })
  const media = ref<Record<string, ProfileMedia>>({})
  const mediaOptions = ref<ProfileMediaOption[]>([])
  const stats = ref<ProfileStats>({ ...EMPTY_STATS })
  const publishedBlocks = ref<ProfileBlock[] | null>(null)
  const isPublic = ref(true)
  const maxBlocks = ref(16)

  const loading = ref(false)
  const saving = ref(false)
  const publishing = ref(false)
  const loadError = ref('')

  // ---------- 历史 ----------
  // 两个基准不能合并：
  //   savedBaseline —— 只在「本地已与服务器一致」时更新（载入/保存/发布/丢弃）
  //   historyBase   —— 撤销栈的栈顶，每记录一次编辑就前移
  // 若共用同一个值，防抖入栈会把 dirty 的基准推到当前态，未保存的修改
  // 会在 400ms 后自己变回「已同步」。
  const savedBaseline = ref(serialize([], { ...DEFAULT_THEME }))
  const historyBase = ref(serialize([], { ...DEFAULT_THEME }))
  const past = ref<string[]>([])
  const future = ref<string[]>([])
  let suppress = true // 载入远端数据时不应入栈

  const canUndo = computed(() => past.value.length > 0)
  const canRedo = computed(() => future.value.length > 0)

  const dirty = computed(() => serialize(blocks.value, theme.value) !== savedBaseline.value)
  const hasUnpublished = computed(() => {
    if (publishedBlocks.value === null) return blocks.value.length > 0
    return JSON.stringify(publishedBlocks.value) !== JSON.stringify(blocks.value)
  })

  let historyTimer: number | undefined

  watch(
    [blocks, theme],
    () => {
      if (suppress) return
      window.clearTimeout(historyTimer)
      historyTimer = window.setTimeout(() => {
        // 计时器排队期间可能发生了程序性重置（保存/撤销/载入），此时不能再入栈
        if (suppress) return
        const now = serialize(blocks.value, theme.value)
        if (now === historyBase.value) return
        past.value.push(historyBase.value)
        if (past.value.length > HISTORY_LIMIT) past.value.shift()
        future.value = []
        historyBase.value = now
      }, HISTORY_DEBOUNCE_MS)
    },
    { deep: true },
  )

  function applySnapshot(raw: string) {
    const snap = JSON.parse(raw) as Snapshot
    suppress = true
    blocks.value = snap.blocks
    theme.value = snap.theme
    // 撤销只移动历史位置，不改变「上次落库」的事实，dirty 应继续保持
    historyBase.value = serialize(blocks.value, theme.value)
    // 深层 watch 在本次刷新里跑，刷新结束后再恢复记录
    void nextTick(() => {
      suppress = false
    })
  }

  function undo() {
    const prev = past.value.pop()
    if (prev === undefined) return
    future.value.push(serialize(blocks.value, theme.value))
    applySnapshot(prev)
  }

  function redo() {
    const next = future.value.pop()
    if (next === undefined) return
    past.value.push(serialize(blocks.value, theme.value))
    applySnapshot(next)
  }

  // 只在「本地态已与服务器一致」时调用：载入、保存、发布、丢弃
  function resetHistory(blocksNow: ProfileBlock[], themeNow: ProfileTheme) {
    // 清掉排队中的防抖计时器，否则它会在重置之后把当前态当成一次新编辑
    window.clearTimeout(historyTimer)
    past.value = []
    future.value = []
    const snap = serialize(blocksNow, themeNow)
    historyBase.value = snap
    savedBaseline.value = snap
  }

  // ---------- 载入 ----------
  async function load() {
    loading.value = true
    loadError.value = ''
    suppress = true
    try {
      const data = await getMyLayout()
      blocks.value = data.draft_blocks ?? []
      theme.value = { ...DEFAULT_THEME, ...data.theme }
      media.value = data.media ?? {}
      stats.value = data.stats ?? { ...EMPTY_STATS }
      publishedBlocks.value = data.published_blocks ?? null
      isPublic.value = data.is_public
      maxBlocks.value = data.max_blocks
      resetHistory(blocks.value, theme.value)
      void loadMediaOptions()
    } catch (e) {
      loadError.value = e instanceof Error ? e.message : '主页配置加载失败'
    } finally {
      loading.value = false
      window.setTimeout(() => {
        suppress = false
      }, 0)
    }
  }

  async function loadMediaOptions() {
    try {
      const data = await getMyMedia()
      mediaOptions.value = data.items ?? []
    } catch {
      // 素材清单失败不阻塞编辑，属性面板会显示为空并提示
      mediaOptions.value = []
    }
  }

  // ---------- 编辑动作 ----------
  function addBlock(type: ProfileBlockType) {
    if (blocks.value.length >= maxBlocks.value) return null
    const block = newBlock(type)
    blocks.value.push(block)
    return block
  }

  function removeBlock(id: string) {
    const i = blocks.value.findIndex((b) => b.id === id)
    if (i >= 0) blocks.value.splice(i, 1)
  }

  function duplicateBlock(id: string): ProfileBlock | null {
    const i = blocks.value.findIndex((b) => b.id === id)
    if (i < 0 || blocks.value.length >= maxBlocks.value) return null
    const copy = newBlock(blocks.value[i].type)
    copy.span = blocks.value[i].span
    copy.props = clone(blocks.value[i].props)
    blocks.value.splice(i + 1, 0, copy)
    return copy
  }

  function moveBlock(from: number, to: number) {
    if (from === to) return
    if (from < 0 || from >= blocks.value.length) return
    if (to < 0 || to >= blocks.value.length) return
    const [item] = blocks.value.splice(from, 1)
    blocks.value.splice(to, 0, item)
  }

  function setSpan(id: string, span: ProfileSpan) {
    const block = blocks.value.find((b) => b.id === id)
    if (block) block.span = span
  }

  function updateProps(id: string, patch: Record<string, unknown>) {
    const block = blocks.value.find((b) => b.id === id)
    if (block) Object.assign(block.props, patch)
  }

  function applyThemePreset(presetId: string) {
    const preset = THEME_PRESETS.find((p) => p.id === presetId)
    if (!preset) return
    theme.value = {
      ...theme.value,
      primary: preset.primary,
      accent: preset.accent,
      background_type: preset.background_type,
      background_blur: preset.background_blur,
      card_style: preset.card_style,
      background_key: preset.background_type === 'image' ? theme.value.background_key : null,
    }
  }

  // ---------- 持久化 ----------
  async function saveDraft() {
    saving.value = true
    try {
      const data = await saveMyLayout({
        blocks: clone(blocks.value),
        is_public: isPublic.value,
      })
      // 主题是独立端点。保存草稿后若只标 blocks 已落库，主题改动会被
      // resetHistory 一并算成「已同步」，实际却没发出去。
      const themeData = await saveMyTheme(clone(theme.value))
      theme.value = { ...DEFAULT_THEME, ...themeData.theme }
      publishedBlocks.value = data.published_blocks ?? publishedBlocks.value
      media.value = data.media ?? media.value
      suppress = true
      resetHistory(blocks.value, theme.value)
      window.setTimeout(() => {
        suppress = false
      }, 0)
    } finally {
      saving.value = false
    }
  }

  async function publish() {
    publishing.value = true
    try {
      // 先把当前草稿与主题落库，再发布，避免发布的是上一版
      await saveMyLayout({ blocks: clone(blocks.value), is_public: isPublic.value })
      await saveMyTheme(clone(theme.value))
      await publishMyLayout()
      publishedBlocks.value = clone(blocks.value)
      suppress = true
      resetHistory(blocks.value, theme.value)
      window.setTimeout(() => {
        suppress = false
      }, 0)
    } finally {
      publishing.value = false
    }
  }

  async function discard() {
    const data = await discardMyDraft()
    suppress = true
    blocks.value = data.draft_blocks ?? []
    theme.value = { ...DEFAULT_THEME, ...data.theme }
    media.value = data.media ?? media.value
    publishedBlocks.value = data.published_blocks ?? null
    resetHistory(blocks.value, theme.value)
    window.setTimeout(() => {
      suppress = false
    }, 0)
  }

  return {
    blocks,
    theme,
    media,
    mediaOptions,
    stats,
    publishedBlocks,
    isPublic,
    maxBlocks,
    loading,
    saving,
    publishing,
    loadError,
    dirty,
    hasUnpublished,
    canUndo,
    canRedo,
    load,
    loadMediaOptions,
    addBlock,
    removeBlock,
    duplicateBlock,
    moveBlock,
    setSpan,
    updateProps,
    applyThemePreset,
    saveDraft,
    publish,
    discard,
    undo,
    redo,
  }
})
