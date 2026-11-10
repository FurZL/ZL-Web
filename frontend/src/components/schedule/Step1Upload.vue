<script setup lang="ts">
import type { ScheduleRecord } from '@/types'

const days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

defineProps<{
  schedules: ScheduleRecord[]
  activeSchedule: ScheduleRecord | null
  uploading: boolean
  uploadError: string
}>()

const emit = defineEmits<{
  select: [schedule: ScheduleRecord]
  toggleShare: [schedule: ScheduleRecord]
  remove: [schedule: ScheduleRecord]
  upload: [file: File]
  clearError: []
  next: []
}>()

function onDrop(e: DragEvent) {
  const f = e.dataTransfer?.files?.[0]
  if (f) emit('upload', f)
}

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  const f = input.files?.[0]
  if (f) emit('upload', f)
  input.value = ''
}

function fmtDate(iso: string | null) {
  return iso ? iso.slice(0, 10) : ''
}
</script>

<template>
  <div class="mt-8 glass-card p-8 max-w-2xl">
    <!-- 已有课表 -->
    <template v-if="schedules.length > 0">
      <h2 class="text-sm font-medium text-sub mb-3">我的课表</h2>
      <div class="space-y-2">
        <div
          v-for="s in schedules"
          :key="s.id"
          class="flex items-center gap-3 rounded-xl px-4 py-3 transition cursor-pointer border"
          :class="activeSchedule?.id === s.id ? 'bg-primary-50 border-primary-300 ring-1 ring-primary-200' : 'bg-white/60 border-white/60 hover:border-primary-200'"
          @click="emit('select', s)"
        >
          <div class="flex-1 min-w-0">
            <p class="text-sm text-ink font-medium truncate">{{ s.original_name || '未命名课表' }}</p>
            <p class="text-xs text-faint mt-0.5">
              {{ s.format?.toUpperCase() }} · {{ s.slots.length }} 门课 · {{ fmtDate(s.created_at) }}
            </p>
          </div>
          <button
            class="text-xs px-2.5 py-1 rounded-full border transition"
            :class="s.is_public ? 'bg-emerald-100 text-emerald-700 border-emerald-300' : 'bg-white text-faint border-gray-200'"
            @click.stop="emit('toggleShare', s)"
          >
            {{ s.is_public ? '公开中' : '私有' }}
          </button>
          <button class="text-xs text-faint hover:text-red-500 transition" @click.stop="emit('remove', s)">
            删除
          </button>
        </div>
      </div>

      <div v-if="activeSchedule" class="mt-6">
        <h3 class="text-sm font-medium text-sub mb-3">课程预览（{{ activeSchedule.slots.length }} 门）</h3>
        <div class="space-y-2 max-h-56 overflow-auto">
          <div v-for="(c, i) in activeSchedule.slots" :key="i" class="flex items-center gap-3 text-sm bg-white/60 rounded-lg px-3 py-2">
            <span class="text-faint text-xs w-8">{{ days[c.weekday] }}</span>
            <span class="text-ink flex-1">{{ c.name }}</span>
            <span class="text-faint text-xs">{{ c.location }} · {{ c.lesson_start }}-{{ c.lesson_end }} 节</span>
          </div>
        </div>
      </div>

      <div class="mt-4 bg-primary-50 rounded-xl p-4 text-sm text-primary-800">
        <p>想让圈友能对比你的课表？把课表设为<span class="font-medium">「公开中」</span>即可。公开后，对方在下一步输入你的用户名就能拉到课表。</p>
      </div>

      <div class="mt-6 flex gap-3">
        <button class="btn-ghost" @click="emit('clearError')">换一份课表</button>
        <button class="btn-primary flex-1" :disabled="!activeSchedule" @click="emit('next')">
          下一步：选择对比对象
        </button>
      </div>
    </template>

    <!-- 空状态：上传 -->
    <div
      class="border-2 border-dashed rounded-xl2 p-14 text-center transition cursor-pointer"
      :class="uploadError ? 'border-red-300 bg-red-50/50' : 'border-primary-200 hover:border-primary-400'"
      @click="($refs.fileInput as HTMLInputElement)?.click()"
      @dragover.prevent
      @drop.prevent="onDrop"
    >
      <input ref="fileInput" type="file" accept=".ics,.txt" class="hidden" @change="onFileChange" />
      <div v-if="uploading" class="flex flex-col items-center">
        <div class="w-10 h-10 border-4 border-primary-200 border-t-primary rounded-full animate-spin"></div>
        <p class="mt-4 text-sm text-sub">正在上传并解析课表…</p>
      </div>
      <div v-else-if="uploadError" class="flex flex-col items-center">
        <div class="w-14 h-14 rounded-full bg-red-100 flex items-center justify-center text-2xl">!</div>
        <p class="mt-3 text-red-600 font-medium">{{ uploadError }}</p>
        <p class="mt-1 text-xs text-faint">点击重新选择文件</p>
      </div>
      <div v-else class="flex flex-col items-center">
        <div class="w-14 h-14 rounded-full bg-primary-50 flex items-center justify-center text-3xl text-primary">📅</div>
        <p class="mt-4 text-ink">拖拽课表文件到这里，或点击选择</p>
        <p class="mt-1 text-sm text-faint">支持 .ics / .txt 文件（PDF 暂未支持）</p>
      </div>
    </div>

    <div v-if="uploadError" class="mt-4">
      <button class="btn-ghost w-full" @click="emit('clearError')">返回</button>
    </div>
  </div>
</template>
