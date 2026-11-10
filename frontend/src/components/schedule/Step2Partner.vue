<script setup lang="ts">
import UserAvatar from '@/components/UserAvatar.vue'
import type { ScheduleRecord } from '@/types'

const days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

defineProps<{
  partner: ScheduleRecord | null
  partnerSearching: boolean
  partnerError: string
  compareError: string
  comparing: boolean
}>()

const emit = defineEmits<{
  search: []
  back: []
  compare: []
}>()

const partnerName = defineModel<string>('partnerName')
</script>

<template>
  <div class="mt-8 glass-card p-8 max-w-2xl">
    <label class="label">输入圈友的用户名</label>
    <div class="flex gap-2">
      <input
        v-model="partnerName"
        class="input flex-1"
        placeholder="例如：fluffy_zjut"
        @keyup.enter="emit('search')"
      />
      <button class="btn-primary !px-5" :disabled="partnerSearching" @click="emit('search')">
        {{ partnerSearching ? '查找中…' : '查找' }}
      </button>
    </div>
    <p class="mt-2 text-xs text-faint">对方需将自己的课表设为「公开中」才能被对比。</p>

    <div v-if="partnerError" class="mt-4 text-sm text-red-600">{{ partnerError }}</div>

    <div v-if="partner" class="mt-4">
      <div class="flex items-center gap-3 p-4 rounded-xl bg-primary-50 ring-2 ring-primary-300">
        <UserAvatar :name="partner.owner?.display_name ?? ''" :size="40" />
        <div class="flex-1">
          <p class="text-sm text-ink font-medium">{{ partner.owner?.display_name }}</p>
          <p class="text-xs text-faint">@{{ partner.owner?.username }} · {{ partner.slots.length }} 门课</p>
        </div>
        <span class="text-primary font-medium text-sm">已选 ✓</span>
      </div>

      <div class="mt-4">
        <h3 class="text-sm font-medium text-sub mb-2">TA 的课程预览</h3>
        <div class="space-y-1.5 max-h-48 overflow-auto">
          <div v-for="(c, i) in partner.slots" :key="i" class="flex items-center gap-3 text-sm bg-white/60 rounded-lg px-3 py-1.5">
            <span class="text-faint text-xs w-8">{{ days[c.weekday] }}</span>
            <span class="text-ink flex-1">{{ c.name }}</span>
            <span class="text-faint text-xs">{{ c.location }} · {{ c.lesson_start }}-{{ c.lesson_end }} 节</span>
          </div>
        </div>
      </div>
    </div>

    <div v-if="compareError" class="mt-4 text-sm text-red-600">{{ compareError }}</div>

    <div class="mt-6 flex gap-3">
      <button class="btn-ghost flex-1" @click="emit('back')">上一步</button>
      <button
        class="btn-primary flex-1"
        :disabled="!partner || comparing"
        :class="{ 'opacity-50 cursor-not-allowed': !partner || comparing }"
        @click="emit('compare')"
      >
        {{ comparing ? '对比中…' : '开始对比' }}
      </button>
    </div>
  </div>
</template>
