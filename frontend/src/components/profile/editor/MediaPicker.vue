<script setup lang="ts">
import { computed, ref } from 'vue'
import { useDialog } from '@/composables/useDialog'
import { setProfileImageDisplayable } from '@/api/profile'
import { useProfileLayoutStore } from '@/stores/profileLayout'

const props = defineProps<{
  modelValue: string[]
  multiple?: boolean
  max?: number
}>()

const emit = defineEmits<{ 'update:modelValue': [keys: string[]] }>()

const store = useProfileLayoutStore()
const { showToast } = useDialog()
const pendingId = ref<string | null>(null)

const options = computed(() => store.mediaOptions)

const selected = computed(() => new Set(props.modelValue))

function toggle(key: string) {
  if (props.multiple) {
    const next = [...props.modelValue]
    const i = next.indexOf(key)
    if (i >= 0) next.splice(i, 1)
    else {
      if (next.length >= (props.max ?? 12)) {
        showToast(`最多选 ${props.max ?? 12} 张`)
        return
      }
      next.push(key)
    }
    emit('update:modelValue', next)
    return
  }
  emit('update:modelValue', [key])
}

async function toggleDisplayable(id: string, value: boolean) {
  pendingId.value = id
  try {
    await setProfileImageDisplayable(id, value)
    const item = store.mediaOptions.find((m) => m.id === id)
    if (item) item.is_displayable = value
    // 素材清单里的地址是服务端给的；公开状态变了要重新取整份清单
    await store.loadMediaOptions()
  } catch (e) {
    showToast(e instanceof Error ? e.message : '设置失败')
  } finally {
    pendingId.value = null
  }
}
</script>

<template>
  <div>
    <div v-if="!options.length" class="rounded-xl border border-dashed border-primary-200 px-4 py-6 text-center">
      <p class="text-xs text-sub">私有相册里还没有图片</p>
      <p class="mt-1 text-[11px] text-faint">先在个人空间上传照片，再回来选素材</p>
    </div>

    <div v-else class="max-h-64 overflow-y-auto pr-1 space-y-1.5">
      <div
        v-for="item in options"
        :key="item.object_key"
        class="rounded-xl border transition"
        :class="selected.has(item.object_key) ? 'border-primary-400 bg-primary-50' : 'border-primary-100 hover:border-primary-200'"
      >
        <button class="w-full flex items-center gap-2.5 px-2 py-2 text-left" @click="toggle(item.object_key)">
          <span class="w-10 h-10 shrink-0 rounded-lg overflow-hidden bg-primary-50 flex items-center justify-center">
            <img v-if="item.thumb_url" :src="item.thumb_url" alt="" class="w-full h-full object-cover" loading="lazy" />
            <span v-else class="text-[10px] text-faint">无图</span>
          </span>
          <span class="flex-1 min-w-0">
            <span class="block text-xs text-ink truncate">{{ item.title || '未命名' }}</span>
            <span class="block text-[10px] text-faint">{{ (item.created_at || '').slice(0, 10) }}</span>
          </span>
          <span
            v-if="selected.has(item.object_key)"
            class="w-4 h-4 shrink-0 rounded-full flex items-center justify-center text-[10px] text-white"
            :style="{ background: 'var(--profile-primary)' }"
          >✓</span>
        </button>

        <label class="flex items-center gap-2 px-2.5 pb-2 cursor-pointer select-none">
          <input
            type="checkbox"
            :checked="item.is_displayable"
            :disabled="pendingId === item.id"
            class="accent-primary"
            @change="toggleDisplayable(item.id, ($event.target as HTMLInputElement).checked)"
          />
          <span class="text-[10px] text-faint">
            {{ item.is_displayable ? '已允许出现在公开主页' : '默认仅自己可见，勾选后才会公开' }}
          </span>
        </label>
      </div>
    </div>
  </div>
</template>
