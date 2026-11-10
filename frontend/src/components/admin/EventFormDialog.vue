<script setup lang="ts">
defineProps<{
  show: boolean
  editing: boolean
  error: string
  saving: boolean
}>()

const emit = defineEmits<{ close: []; save: [] }>()

const form = defineModel<{
  title: string
  description: string
  location: string
  starts_at: string
  ends_at: string
  capacity: string | number
  registration_starts_at: string
  registration_ends_at: string
  publish_now: boolean
}>('form', { required: true })
</script>

<template>
  <Teleport to="body">
    <div v-if="show" class="dialog-overlay" @click.self="emit('close')">
      <div class="glass-card p-6 w-full max-w-lg max-h-[85vh] overflow-auto">
        <h2 class="text-lg font-bold text-ink">{{ editing ? '编辑活动' : '新建活动' }}</h2>
        <div v-if="error" class="mt-3 text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{{ error }}</div>
        <div class="mt-4 space-y-4">
          <div>
            <label class="label">活动标题</label>
            <input v-model="form.title" class="input" placeholder="活动标题" />
          </div>
          <div>
            <label class="label">描述</label>
            <textarea v-model="form.description" class="input min-h-[80px]" rows="3" placeholder="活动描述…"></textarea>
          </div>
          <div>
            <label class="label">地点</label>
            <input v-model="form.location" class="input" placeholder="活动地点" />
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="label">开始时间</label>
              <input v-model="form.starts_at" type="datetime-local" class="input" />
            </div>
            <div>
              <label class="label">结束时间</label>
              <input v-model="form.ends_at" type="datetime-local" class="input" />
            </div>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="label">报名开始（可选）</label>
              <input v-model="form.registration_starts_at" type="datetime-local" class="input" />
            </div>
            <div>
              <label class="label">报名截止（可选）</label>
              <input v-model="form.registration_ends_at" type="datetime-local" class="input" />
            </div>
          </div>
          <div>
            <label class="label">人数上限（留空不限）</label>
            <input v-model="form.capacity" type="number" class="input" placeholder="不限" min="1" />
          </div>
          <label v-if="!editing" class="flex items-center gap-2 text-sm text-sub cursor-pointer">
            <input v-model="form.publish_now" type="checkbox" class="accent-primary" />
            立即发布
          </label>
        </div>
        <div class="mt-6 flex gap-3">
          <button class="btn-ghost flex-1" @click="emit('close')">取消</button>
          <button class="btn-primary flex-1" :disabled="saving" @click="emit('save')">
            {{ saving ? '保存中…' : '保存' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
