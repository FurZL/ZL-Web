<script setup lang="ts">
import { ref, watch } from 'vue'
import { request } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

const props = defineProps<{ show: boolean }>()
const emit = defineEmits<{ close: [] }>()

const auth = useAuthStore()
const editName = ref('')
const editBio = ref('')
const editError = ref('')
const saving = ref(false)

watch(() => props.show, (val) => {
  if (val) {
    editName.value = auth.user?.displayName ?? ''
    editBio.value = auth.user?.bio ?? ''
    editError.value = ''
  }
})

async function saveProfile() {
  if (!editName.value.trim()) {
    editError.value = '昵称不能为空'
    return
  }
  saving.value = true
  editError.value = ''
  try {
    await request({
      method: 'PUT',
      url: '/profile/me',
      data: { display_name: editName.value.trim(), bio: editBio.value.trim() },
    })
    await auth.fetchMe()
    emit('close')
  } catch (e) {
    editError.value = e instanceof Error ? e.message : '保存失败'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <div v-if="show" class="dialog-overlay" @click.self="emit('close')">
      <div class="glass-card p-6 w-full max-w-md">
        <h2 class="text-lg font-bold text-ink">编辑资料</h2>
        <div v-if="editError" class="mt-3 text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{{ editError }}</div>
        <div class="mt-4 space-y-4">
          <div>
            <label class="label">昵称</label>
            <input v-model="editName" class="input" placeholder="大家怎么称呼你" maxlength="64" />
          </div>
          <div>
            <label class="label">简介</label>
            <textarea v-model="editBio" class="input min-h-[80px]" rows="3" placeholder="介绍一下自己…" maxlength="500"></textarea>
          </div>
        </div>
        <div class="mt-6 flex gap-3">
          <button class="btn-ghost flex-1" :disabled="saving" @click="emit('close')">取消</button>
          <button class="btn-primary flex-1" :disabled="saving" @click="saveProfile">
            {{ saving ? '保存中…' : '保存' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
