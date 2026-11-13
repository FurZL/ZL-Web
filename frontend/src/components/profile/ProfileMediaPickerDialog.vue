<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { getMyMedia, setProfileImageDisplayable } from '@/api/profile'
import { useDialog } from '@/composables/useDialog'
import type { ProfileMediaOption } from '@/types'

const props = defineProps<{ show: boolean }>()
const emit = defineEmits<{ close: []; changed: [] }>()

const { showToast } = useDialog()

const items = ref<ProfileMediaOption[]>([])
const loading = ref(false)
const loadError = ref('')
const pendingId = ref<string | null>(null)
const changed = ref(false)

const publicCount = computed(() => items.value.filter((i) => i.is_displayable).length)

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const data = await getMyMedia()
    items.value = data.items ?? []
  } catch (e) {
    loadError.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

watch(
  () => props.show,
  (val) => {
    if (!val) {
      if (changed.value) emit('changed')
      return
    }
    changed.value = false
    void load()
  },
)

async function toggle(item: ProfileMediaOption) {
  const next = !item.is_displayable
  pendingId.value = item.id
  try {
    await setProfileImageDisplayable(item.id, next)
    item.is_displayable = next
    changed.value = true
  } catch (e) {
    showToast(e instanceof Error ? e.message : '设置失败')
  } finally {
    pendingId.value = null
  }
}
</script>

<template>
  <Teleport to="body">
    <div v-if="show" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/40 backdrop-blur-sm" @click.self="emit('close')">
      <div class="glass-card max-w-2xl w-full p-6 max-h-[85vh] flex flex-col">
        <div class="flex items-start justify-between gap-3">
          <div>
            <h2 class="text-lg font-bold text-ink">公开素材</h2>
            <p class="mt-1 text-xs text-sub">
              只有勾选的图片能被主页模块引用并展示给访客（当前 {{ publicCount }} 张公开）
            </p>
          </div>
          <button class="text-faint hover:text-ink" @click="emit('close')">✕</button>
        </div>

        <div class="mt-4 flex-1 overflow-y-auto pr-1">
          <div v-if="loading" class="py-12 text-center text-sub text-sm">加载中…</div>
          <p v-else-if="loadError" class="py-12 text-center text-blush text-sm">{{ loadError }}</p>
          <p v-else-if="!items.length" class="py-12 text-center text-sub text-sm">私有相册里还没有图片</p>

          <div v-else class="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <div v-for="item in items" :key="item.id" class="rounded-xl border border-primary-100 overflow-hidden">
              <div class="aspect-square bg-primary-50 flex items-center justify-center">
                <img v-if="item.thumb_url" :src="item.thumb_url" alt="" class="w-full h-full object-cover" loading="lazy" />
                <span v-else class="text-xs text-faint">无预览</span>
              </div>
              <div class="p-2">
                <p class="text-xs text-ink truncate">{{ item.title || '未命名' }}</p>
                <button
                  class="mt-1.5 w-full rounded-lg px-2 py-1 text-[11px] border transition disabled:opacity-50"
                  :class="item.is_displayable
                    ? 'text-white border-transparent'
                    : 'text-sub border-primary-200 hover:border-primary-400'"
                  :style="item.is_displayable ? { background: 'var(--profile-primary)' } : undefined"
                  :disabled="pendingId === item.id"
                  @click="toggle(item)"
                >
                  {{ pendingId === item.id ? '…' : item.is_displayable ? '已公开' : '设为公开' }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <div class="mt-4 flex justify-end">
          <button class="btn-primary !px-5 !py-2 text-sm" @click="emit('close')">完成</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
