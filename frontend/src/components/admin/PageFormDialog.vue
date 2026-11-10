<script setup lang="ts">
import { computed } from 'vue'

defineProps<{
  show: boolean
  editing: boolean
  error: string
  saving: boolean
}>()

const emit = defineEmits<{ close: []; save: [] }>()

const form = defineModel<{
  slug: string
  title: string
  seo_title: string
  seo_description: string
  schemaText: string
}>('form', { required: true })

const schemaError = computed(() => {
  if (!form.value.schemaText.trim()) return ''
  try {
    const parsed = JSON.parse(form.value.schemaText)
    if (typeof parsed !== 'object' || parsed === null) return 'Schema 必须是 JSON 对象'
    return ''
  } catch {
    return 'JSON 格式有误，请检查'
  }
})
</script>

<template>
  <Teleport to="body">
    <div v-if="show" class="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4" @click.self="emit('close')">
      <div class="glass-card p-6 w-full max-w-2xl max-h-[85vh] overflow-auto">
        <h2 class="text-lg font-bold text-ink">{{ editing ? '编辑页面' : '新建页面' }}</h2>
        <div v-if="error" class="mt-3 text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{{ error }}</div>
        <div class="mt-4 space-y-4">
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="label">Slug（URL 路径，仅小写字母/数字/短横线）</label>
              <input v-model="form.slug" class="input" placeholder="welcome-party-2026" :disabled="editing" />
            </div>
            <div>
              <label class="label">页面标题</label>
              <input v-model="form.title" class="input" placeholder="页面标题" />
            </div>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="label">SEO 标题（可选）</label>
              <input v-model="form.seo_title" class="input" />
            </div>
            <div>
              <label class="label">SEO 描述（可选）</label>
              <input v-model="form.seo_description" class="input" />
            </div>
          </div>
          <div>
            <label class="label">页面 Schema（JSON）</label>
            <textarea v-model="form.schemaText" class="input font-mono text-xs min-h-[240px]" rows="16" spellcheck="false"></textarea>
            <p v-if="schemaError" class="mt-1 text-xs text-red-500">{{ schemaError }}</p>
            <p v-else class="mt-1 text-xs text-faint">
              支持组件：hero / rich_text / image / countdown / button / notice / event_info / card / divider
            </p>
          </div>
        </div>
        <div class="mt-6 flex gap-3">
          <button class="btn-ghost flex-1" @click="emit('close')">取消</button>
          <button class="btn-primary flex-1" :disabled="saving || !!schemaError" @click="emit('save')">
            {{ saving ? '保存中…' : '保存' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
