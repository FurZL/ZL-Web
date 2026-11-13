<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { onBeforeRouteLeave, useRouter } from 'vue-router'
import ModuleLibrary from '@/components/profile/editor/ModuleLibrary.vue'
import PreviewCanvas from '@/components/profile/editor/PreviewCanvas.vue'
import PropertyPanel from '@/components/profile/editor/PropertyPanel.vue'
import ThemePanel from '@/components/profile/editor/ThemePanel.vue'
import ProfileRenderer from '@/components/profile/ProfileRenderer.vue'
import { useProfileLayoutStore } from '@/stores/profileLayout'
import { useDialog } from '@/composables/useDialog'
import type { ProfileBlockType, ProfileSpan } from '@/types'

const router = useRouter()
const store = useProfileLayoutStore()
const { showToast, showConfirm } = useDialog()

const selectedId = ref<string | null>(null)
const previewing = ref(false)
const themeOpen = ref(false)

const remaining = computed(() => Math.max(0, store.maxBlocks - store.blocks.length))

const backgroundUrl = computed(() => {
  const key = store.theme.background_key
  if (!key) return null
  const m = store.media[key]
  return m?.display_url ?? m?.thumb_url ?? null
})

function addBlock(type: ProfileBlockType) {
  const created = store.addBlock(type)
  if (!created) {
    showToast(`最多 ${store.maxBlocks} 个模块`)
    return
  }
  selectedId.value = created.id
}

function move(from: number, to: number) {
  store.moveBlock(from, to)
}

function remove(id: string) {
  store.removeBlock(id)
  if (selectedId.value === id) selectedId.value = null
}

function duplicate(id: string) {
  const copy = store.duplicateBlock(id)
  if (!copy) {
    showToast(`最多 ${store.maxBlocks} 个模块`)
    return
  }
  selectedId.value = copy.id
}

function setSpan(span: ProfileSpan) {
  if (selectedId.value) store.setSpan(selectedId.value, span)
}

async function onSaveDraft() {
  try {
    await store.saveDraft()
    showToast('草稿已保存')
  } catch (e) {
    showToast(e instanceof Error ? e.message : '保存失败')
  }
}

async function onPublish() {
  if (!(await showConfirm('发布会用当前草稿覆盖访客看到的版本，确定发布吗？'))) return
  try {
    await store.publish()
    showToast('已发布')
  } catch (e) {
    showToast(e instanceof Error ? e.message : '发布失败')
  }
}

async function onDiscard() {
  if (!(await showConfirm('丢弃草稿会回到上次发布的版本，确定吗？'))) return
  try {
    await store.discard()
    selectedId.value = null
    showToast('草稿已丢弃')
  } catch (e) {
    showToast(e instanceof Error ? e.message : '操作失败')
  }
}

function onKeydown(e: KeyboardEvent) {
  const mod = e.ctrlKey || e.metaKey
  if (!mod) return
  if (e.key.toLowerCase() === 'z' && !e.shiftKey) {
    e.preventDefault()
    store.undo()
  } else if ((e.key.toLowerCase() === 'z' && e.shiftKey) || e.key.toLowerCase() === 'y') {
    e.preventDefault()
    store.redo()
  }
}

function onBeforeUnload(e: BeforeUnloadEvent) {
  if (!store.dirty) return
  e.preventDefault()
  e.returnValue = ''
}

onMounted(() => {
  void store.load()
  window.addEventListener('keydown', onKeydown)
  window.addEventListener('beforeunload', onBeforeUnload)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  window.removeEventListener('beforeunload', onBeforeUnload)
})

onBeforeRouteLeave(async () => {
  if (!store.dirty) return true
  return await showConfirm('还有未保存的修改，确定离开吗？')
})
</script>

<template>
  <div class="max-w-[1400px] mx-auto px-4 py-6">
    <!-- 顶栏 -->
    <div class="glass-card px-4 py-3 flex flex-wrap items-center gap-2">
      <button class="btn-ghost !px-3 !py-1.5 !text-xs" @click="router.push('/profile')">← 返回</button>
      <div class="flex-1 min-w-0">
        <h1 class="text-base font-bold text-ink">编辑我的主页</h1>
        <p class="text-[11px] text-faint">
          <template v-if="store.dirty">有未保存的修改</template>
          <template v-else-if="store.hasUnpublished">草稿已保存，尚未发布</template>
          <template v-else>已与线上同步</template>
        </p>
      </div>

      <div class="flex items-center gap-1.5">
        <button class="btn-ghost !px-2.5 !py-1.5 !text-xs" :disabled="!store.canUndo" title="撤销 Ctrl+Z" @click="store.undo()">↶</button>
        <button class="btn-ghost !px-2.5 !py-1.5 !text-xs" :disabled="!store.canRedo" title="重做 Ctrl+Shift+Z" @click="store.redo()">↷</button>
        <button class="btn-ghost !px-3 !py-1.5 !text-xs" :disabled="store.saving" @click="onSaveDraft">
          {{ store.saving ? '保存中…' : '保存草稿' }}
        </button>
        <button class="btn-ghost !px-3 !py-1.5 !text-xs" @click="previewing = true">预览</button>
        <button class="btn-primary !px-4 !py-1.5 !text-xs" :disabled="store.publishing" @click="onPublish">
          {{ store.publishing ? '发布中…' : '发布' }}
        </button>
      </div>
    </div>

    <div v-if="store.loading" class="mt-10 text-center text-sub py-20">加载中…</div>
    <div v-else-if="store.loadError" class="mt-6 glass-card p-8 text-center">
      <p class="text-blush">{{ store.loadError }}</p>
      <button class="btn-ghost mt-4 !px-4 !py-2 text-sm" @click="store.load()">重试</button>
    </div>

    <div v-else class="mt-4 grid gap-4 lg:grid-cols-[210px_minmax(0,1fr)_300px] items-start">
      <!-- 左：模块库（手机上折叠到画布上方） -->
      <div class="lg:sticky lg:top-4">
        <ModuleLibrary :remaining="remaining" @add="addBlock" />
      </div>

      <!-- 中：画布 -->
      <div class="min-w-0">
        <PreviewCanvas
          :blocks="store.blocks"
          :selected-id="selectedId"
          :theme="store.theme"
          :media="store.media"
          :stats="store.stats"
          :background-url="backgroundUrl"
          @select="selectedId = $event"
          @move="move"
          @remove="remove"
          @duplicate="duplicate"
        />

        <div class="mt-3 flex flex-wrap items-center justify-between gap-2 text-[11px] text-faint">
          <span>拖拽模块可调整顺序，也可用模块右上角 ↑↓。宽度在右侧切换。</span>
          <button class="hover:text-blush disabled:opacity-40" :disabled="!store.publishedBlocks" @click="onDiscard">丢弃草稿</button>
        </div>
      </div>

      <!-- 右：属性 + 主题 -->
      <div class="space-y-3 lg:sticky lg:top-4">
        <PropertyPanel :block-id="selectedId" @update:span="setSpan" />

        <div class="glass-card">
          <button class="w-full flex items-center justify-between px-4 py-3 text-sm font-semibold text-ink" @click="themeOpen = !themeOpen">
            <span>外观与背景</span>
            <span class="text-faint text-xs">{{ themeOpen ? '收起' : '展开' }}</span>
          </button>
          <div v-if="themeOpen" class="px-4 pb-4">
            <ThemePanel />
          </div>
        </div>
      </div>
    </div>

    <!-- 预览弹层 -->
    <Teleport to="body">
      <div v-if="previewing" class="fixed inset-0 z-50 bg-ink/50 backdrop-blur-sm overflow-y-auto" @click.self="previewing = false">
        <div class="max-w-4xl mx-auto my-8 px-4">
          <div class="flex items-center justify-between text-white mb-3">
            <span class="text-sm">访客看到的样子（草稿态，尚未发布）</span>
            <button class="text-white/80 hover:text-white" @click="previewing = false">✕</button>
          </div>
          <ProfileRenderer
            :theme="store.theme"
            :blocks="store.blocks"
            :media="store.media"
            :stats="store.stats"
            :background-url="backgroundUrl"
          />
        </div>
      </div>
    </Teleport>
  </div>
</template>
