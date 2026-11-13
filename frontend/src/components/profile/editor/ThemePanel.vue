<script setup lang="ts">
import { computed } from 'vue'
import type { ProfileCardStyle } from '@/types'
import { THEME_PRESETS } from '../theme'
import { useProfileLayoutStore } from '@/stores/profileLayout'
import MediaPicker from './MediaPicker.vue'

const store = useProfileLayoutStore()

const theme = computed(() => store.theme)

const activePreset = computed(() => {
  const t = theme.value
  const hit = THEME_PRESETS.find(
    (p) =>
      p.primary.toLowerCase() === t.primary.toLowerCase() &&
      p.accent.toLowerCase() === t.accent.toLowerCase() &&
      p.background_type === t.background_type &&
      p.card_style === t.card_style,
  )
  return hit?.id ?? ''
})

const CARD_STYLES: { id: ProfileCardStyle; name: string }[] = [
  { id: 'glass', name: '玻璃' },
  { id: 'solid', name: '纯白' },
  { id: 'outline', name: '描边' },
]

function set<K extends keyof typeof store.theme>(key: K, value: (typeof store.theme)[K]) {
  store.theme[key] = value
}

function setBackgroundType(type: 'solid' | 'gradient' | 'image') {
  store.theme.background_type = type
  if (type !== 'image') store.theme.background_key = null
}

function setBackgroundKey(keys: string[]) {
  store.theme.background_key = keys[0] ?? null
}
</script>

<template>
  <div class="glass-card p-4">
    <h2 class="text-sm font-semibold text-ink">外观</h2>

    <!-- 预设 -->
    <div class="mt-3">
      <label class="label !text-xs">配色预设</label>
      <div class="grid grid-cols-2 gap-1.5">
        <button
          v-for="p in THEME_PRESETS"
          :key="p.id"
          class="flex items-center gap-2 rounded-xl border px-2 py-1.5 transition"
          :class="activePreset === p.id ? 'border-primary-400 bg-primary-50' : 'border-primary-100 hover:border-primary-300'"
          @click="store.applyThemePreset(p.id)"
        >
          <span class="w-4 h-4 rounded-full shrink-0" :style="{ background: `linear-gradient(135deg, ${p.primary}, ${p.accent})` }"></span>
          <span class="text-[11px] text-ink">{{ p.name }}</span>
        </button>
      </div>
    </div>

    <!-- 自定义色 -->
    <div class="mt-4 grid grid-cols-2 gap-2">
      <div>
        <label class="label !text-xs">主色</label>
        <div class="flex items-center gap-1.5">
          <input
            type="color"
            class="w-8 h-8 rounded-lg border border-primary-100 bg-white p-0.5 cursor-pointer"
            :value="theme.primary"
            @input="set('primary', ($event.target as HTMLInputElement).value)"
          />
          <span class="text-[10px] text-faint font-mono">{{ theme.primary.toUpperCase() }}</span>
        </div>
      </div>
      <div>
        <label class="label !text-xs">点缀色</label>
        <div class="flex items-center gap-1.5">
          <input
            type="color"
            class="w-8 h-8 rounded-lg border border-primary-100 bg-white p-0.5 cursor-pointer"
            :value="theme.accent"
            @input="set('accent', ($event.target as HTMLInputElement).value)"
          />
          <span class="text-[10px] text-faint font-mono">{{ theme.accent.toUpperCase() }}</span>
        </div>
      </div>
    </div>

    <!-- 背景 -->
    <div class="mt-4">
      <label class="label !text-xs">背景</label>
      <div class="flex gap-1.5">
        <button
          v-for="opt in [{ id: 'solid', name: '纯色' }, { id: 'gradient', name: '渐变' }, { id: 'image', name: '图片' }]"
          :key="opt.id"
          class="flex-1 px-2 py-1 rounded-lg text-[11px] border transition"
          :class="theme.background_type === opt.id ? 'text-white border-transparent' : 'text-sub border-primary-100 hover:border-primary-300'"
          :style="theme.background_type === opt.id ? { background: 'var(--profile-primary)' } : undefined"
          @click="setBackgroundType(opt.id as 'solid' | 'gradient' | 'image')"
        >{{ opt.name }}</button>
      </div>

      <div v-if="theme.background_type === 'image'" class="mt-2 space-y-2">
        <MediaPicker :model-value="theme.background_key ? [theme.background_key] : []" @update:model-value="setBackgroundKey" />
        <div v-if="theme.background_key">
          <label class="label !text-xs">模糊 {{ theme.background_blur }}px</label>
          <input
            type="range"
            min="0"
            max="20"
            step="1"
            class="w-full accent-primary"
            :value="theme.background_blur"
            @input="set('background_blur', Number(($event.target as HTMLInputElement).value))"
          />
        </div>
        <p v-else class="text-[10px] text-faint">先选一张背景图</p>
      </div>
    </div>

    <!-- 卡片 -->
    <div class="mt-4">
      <label class="label !text-xs">模块卡片</label>
      <div class="flex gap-1.5">
        <button
          v-for="c in CARD_STYLES"
          :key="c.id"
          class="flex-1 px-2 py-1 rounded-lg text-[11px] border transition"
          :class="theme.card_style === c.id ? 'text-white border-transparent' : 'text-sub border-primary-100 hover:border-primary-300'"
          :style="theme.card_style === c.id ? { background: 'var(--profile-primary)' } : undefined"
          @click="set('card_style', c.id)"
        >{{ c.name }}</button>
      </div>
    </div>
  </div>
</template>
