<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useDialog } from '@/composables/useDialog'
import Step1Upload from '@/components/schedule/Step1Upload.vue'
import Step2Partner from '@/components/schedule/Step2Partner.vue'
import Step3Result from '@/components/schedule/Step3Result.vue'
import {
  compareSchedules,
  completeScheduleUpload,
  createScheduleUploadIntent,
  deleteSchedule,
  getMySchedules,
  getSharedSchedule,
  setScheduleVisibility,
} from '@/api/schedule'
import type { ScheduleCompareResult, ScheduleRecord, ScheduleSlot } from '@/types'

const step = ref(1)
const { showToast, showConfirm } = useDialog()

// ---------- 我的课表 ----------
const mySchedules = ref<ScheduleRecord[]>([])
const activeSchedule = ref<ScheduleRecord | null>(null)
const loadingMine = ref(true)

async function loadMine() {
  loadingMine.value = true
  try {
    const data = await getMySchedules()
    mySchedules.value = data.items
    if (!activeSchedule.value && data.items.length > 0) {
      activeSchedule.value = data.items[0]
    }
    if (activeSchedule.value) {
      const fresh = data.items.find((s) => s.id === activeSchedule.value!.id)
      activeSchedule.value = fresh ?? data.items[0] ?? null
    }
  } catch (e) {
    showToast(e instanceof Error ? e.message : '课表加载失败')
  } finally {
    loadingMine.value = false
  }
}

onMounted(loadMine)

const mySlots = computed<ScheduleSlot[]>(() => activeSchedule.value?.slots ?? [])

// ---------- 上传 ----------
const uploading = ref(false)
const uploadError = ref('')

async function uploadFile(f: File) {
  const name = f.name.toLowerCase()
  if (!name.endsWith('.ics') && !name.endsWith('.txt')) {
    uploadError.value = '仅支持 .ics / .txt 文件（PDF 暂未支持）'
    return
  }
  uploading.value = true
  uploadError.value = ''
  try {
    const intent = await createScheduleUploadIntent(f.name, f.size)
    const put = await fetch(intent.upload_url, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/octet-stream' },
      body: f,
    })
    if (!put.ok) throw new Error('文件上传到存储失败，请重试')
    const record = await completeScheduleUpload(intent, f.name)
    mySchedules.value = [record, ...mySchedules.value]
    activeSchedule.value = record
  } catch (e) {
    uploadError.value = e instanceof Error ? e.message : '上传失败'
  } finally {
    uploading.value = false
  }
}

// ---------- 分享 / 删除 ----------
async function toggleShare(s: ScheduleRecord) {
  try {
    const updated = await setScheduleVisibility(s.id, !s.is_public)
    const idx = mySchedules.value.findIndex((x) => x.id === s.id)
    if (idx >= 0) mySchedules.value[idx] = updated
    if (activeSchedule.value?.id === s.id) activeSchedule.value = updated
  } catch (e) {
    showToast(e instanceof Error ? e.message : '操作失败')
  }
}

async function removeSchedule(s: ScheduleRecord) {
  if (!(await showConfirm(`确定删除课表「${s.original_name ?? '未命名'}」吗？`))) return
  try {
    await deleteSchedule(s.id)
    mySchedules.value = mySchedules.value.filter((x) => x.id !== s.id)
    if (activeSchedule.value?.id === s.id) {
      activeSchedule.value = mySchedules.value[0] ?? null
    }
  } catch (e) {
    showToast(e instanceof Error ? e.message : '删除失败')
  }
}

// ---------- 对比对象 ----------
const partnerName = ref('')
const partnerSearching = ref(false)
const partnerError = ref('')
const partner = ref<ScheduleRecord | null>(null)

async function searchPartner() {
  const q = partnerName.value.trim()
  if (!q) return
  partnerSearching.value = true
  partnerError.value = ''
  partner.value = null
  try {
    partner.value = await getSharedSchedule(q)
  } catch (e) {
    partnerError.value = e instanceof Error ? e.message : '未找到该用户公开的课表'
  } finally {
    partnerSearching.value = false
  }
}

const partnerSlots = computed<ScheduleSlot[]>(() => partner.value?.slots ?? [])

// ---------- 对比结果 ----------
const comparing = ref(false)
const compareError = ref('')
const result = ref<ScheduleCompareResult | null>(null)

async function runCompare() {
  if (!activeSchedule.value || !partner.value) return
  comparing.value = true
  compareError.value = ''
  try {
    result.value = await compareSchedules(mySlots.value, partnerSlots.value)
    step.value = 3
  } catch (e) {
    compareError.value = e instanceof Error ? e.message : '对比失败'
  } finally {
    comparing.value = false
  }
}
</script>

<template>
  <div class="max-w-6xl mx-auto px-4 py-10">
    <h1 class="text-3xl font-bold text-ink">课表对比工具</h1>
    <p class="mt-2 text-sub">上传课表，和圈友对比空闲时间，约上一起玩。</p>

    <!-- 步骤指示 -->
    <div class="mt-8 flex items-center gap-2 text-sm">
      <template v-for="(label, i) in ['上传课表', '选择对象', '查看结果']" :key="label">
        <div class="flex items-center gap-2">
          <span
            class="w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium"
            :class="step > i ? 'bg-primary text-white' : step === i + 1 ? 'bg-primary-200 text-primary-800' : 'bg-white/70 text-faint border border-white/60'"
          >
            {{ i + 1 }}
          </span>
          <span :class="step === i + 1 ? 'text-ink font-medium' : 'text-faint'">{{ label }}</span>
        </div>
        <span v-if="i < 2" class="w-8 h-px bg-primary-200"></span>
      </template>
    </div>

    <!-- Step 1 -->
    <Step1Upload
      v-if="step === 1"
      :schedules="mySchedules"
      :active-schedule="activeSchedule"
      :uploading="uploading"
      :upload-error="uploadError"
      @select="activeSchedule = $event"
      @toggle-share="toggleShare"
      @remove="removeSchedule"
      @upload="uploadFile"
      @clear-error="uploadError = ''"
      @next="step = 2"
    />

    <!-- Step 2 -->
    <Step2Partner
      v-else-if="step === 2"
      v-model:partner-name="partnerName"
      :partner="partner"
      :partner-searching="partnerSearching"
      :partner-error="partnerError"
      :compare-error="compareError"
      :comparing="comparing"
      @search="searchPartner"
      @back="step = 1"
      @compare="runCompare"
    />

    <!-- Step 3 -->
    <Step3Result
      v-else
      :my-schedule="activeSchedule"
      :partner="partner"
      :result="result"
      @back="step = 2"
    />
  </div>
</template>
