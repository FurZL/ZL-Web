<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { AppointmentDetail, ScheduleRecord } from '@/types'

const props = defineProps<{
  invitation: AppointmentDetail | null
  schedules: ScheduleRecord[]
  activeSchedule: ScheduleRecord | null
  saving: boolean
  error: string
}>()

const emit = defineEmits<{
  close: []
  respond: [id: string, accepted: boolean, scheduleId?: string]
  cancel: [id: string]
}>()

const selectedScheduleId = ref('')
const localError = ref('')

watch(
  () => [props.activeSchedule?.id, props.invitation?.id] as const,
  () => {
    selectedScheduleId.value = props.activeSchedule?.id ?? ''
    localError.value = ''
  },
  { immediate: true },
)

const fixedLabel = computed(() => {
  const fixed = props.invitation?.fixed
  if (!fixed) return ''
  const format = (value: string) => new Intl.DateTimeFormat('zh-CN', {
    timeZone: 'Asia/Shanghai', month: 'numeric', day: 'numeric', weekday: 'short',
  }).format(new Date(value))
  const clock = (value: string) => new Intl.DateTimeFormat('zh-CN', {
    timeZone: 'Asia/Shanghai', hour: '2-digit', minute: '2-digit', hour12: false,
  }).format(new Date(value))
  return `${format(fixed.starts_at)} ${clock(fixed.starts_at)}–${clock(fixed.ends_at)}`
})

const otherName = computed(() => {
  if (props.invitation?.is_group) return props.invitation.participants.find(item => item.role === 'organizer')?.username ?? '群组成员'
  const participant = props.invitation?.participants.find(item => item.role !== (props.invitation?.viewer_participant.role ?? 'invitee'))
  return participant?.username ?? '对方'
})

const canAccept = computed(() => props.invitation?.status === 'pending'
  && props.invitation.viewer_participant.status === 'invited')

function accept() {
  if (!props.invitation || !canAccept.value) return
  if (!selectedScheduleId.value) {
    localError.value = '请先选择一份课表'
    return
  }
  localError.value = ''
  emit('respond', props.invitation.id, true, selectedScheduleId.value)
}

function decline() {
  if (props.invitation) emit('respond', props.invitation.id, false)
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="invitation"
      class="dialog-overlay invitation-dialog-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="invitation-title"
      @click.self="!saving && emit('close')"
      @keydown.esc.stop="!saving && emit('close')"
    >
      <form class="space-y-4 p-5 sm:p-6" @submit.prevent="accept">
        <div class="flex items-start justify-between gap-3">
          <div>
            <p class="text-xs font-semibold uppercase tracking-[0.16em] text-amber-600">Invitation</p>
            <h2 id="invitation-title" class="mt-1 text-xl font-bold text-ink">{{ invitation.title }}</h2>
            <p class="mt-1 text-sm text-sub">{{ otherName }} 发来的约定邀请</p>
          </div>
          <button type="button" class="btn-sm" aria-label="关闭约定邀请" :disabled="saving" @click="emit('close')">✕</button>
        </div>

        <div class="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
          <p class="text-sm font-semibold text-amber-900">{{ fixedLabel }}</p>
          <p class="mt-1 text-xs text-amber-700">
            {{ invitation.fixed?.week ? `第 ${invitation.fixed.week} 周` : '约定时间' }}
            <template v-if="invitation.location"> · {{ invitation.location }}</template>
          </p>
        </div>

        <p v-if="invitation.notice" class="rounded-xl bg-primary-50 px-3 py-2 text-sm text-sub">{{ invitation.notice }}</p>
        <div v-if="invitation.is_group" class="text-sm text-sub">
          <p class="font-medium text-ink">参与成员</p>
          <p v-for="person in invitation.participants" :key="person.username" class="mt-1">{{ person.username }} · {{ person.status === 'accepted' ? '已接受' : person.status === 'declined' ? '已婉拒' : '待回应' }}</p>
        </div>

        <template v-if="canAccept">
          <label class="label">参与约定的课表
            <select v-model="selectedScheduleId" class="input mt-1" :disabled="saving">
              <option disabled value="">请选择一份课表</option>
              <option v-for="schedule in schedules" :key="schedule.id" :value="schedule.id">
                {{ schedule.original_name || '未命名课表' }}
              </option>
            </select>
          </label>
          <p class="text-xs leading-5 text-sub">{{ invitation.is_group ? '接受后将等待其他成员回应，全部接受并复核通过后加入各自日程。' : '接受后会重新核对双方课表和已有日程；通过后自动加入双方「我的日程」。' }}</p>
          <p v-if="localError || error" role="alert" class="text-sm text-red-600">{{ localError || error }}</p>
          <div class="flex flex-wrap justify-end gap-2 pt-1">
            <button type="button" class="btn-ghost" :disabled="saving" @click="decline">婉拒</button>
            <button type="submit" class="btn-primary" :disabled="saving || !selectedScheduleId">
              {{ saving ? '处理中…' : invitation.is_group ? '接受邀请' : '接受并加入双方日程' }}
            </button>
          </div>
        </template>

        <template v-else-if="invitation.status === 'pending'">
          <p class="text-sm text-sub">{{ invitation.is_group ? '等待所有成员接受。全部接受后会重新核对时间。' : '邀请已经发出，等待对方接受。接受后会自动加入双方日程。' }}</p>
          <p v-if="error" role="alert" class="text-sm text-red-600">{{ error }}</p>
          <div class="flex justify-end">
            <button v-if="invitation.viewer_participant.role === 'organizer'" type="button" class="btn-sm-danger" :disabled="saving" @click="emit('cancel', invitation.id)">取消这次约定</button>
          </div>
        </template>

        <template v-else>
          <p class="text-sm text-sub">{{ invitation.status === 'confirmed' ? '约定已确认，已加入参与者日程。' : `这次邀请状态：${invitation.status}` }}</p>
          <p v-if="error" role="alert" class="text-sm text-red-600">{{ error }}</p>
          <div class="flex justify-end gap-2">
            <button v-if="invitation.is_group && invitation.status === 'confirmed'" type="button" class="btn-sm-danger" :disabled="saving" @click="emit('cancel', invitation.id)">取消这次约定</button>
            <button type="button" class="btn-sm" @click="emit('close')">关闭</button>
          </div>
        </template>
      </form>
    </div>
  </Teleport>
</template>

<style scoped>
.invitation-dialog-overlay {
  background: rgb(31 27 51 / 42%);
  backdrop-filter: blur(4px);
}

.invitation-dialog-overlay > form {
  width: min(30rem, calc(100vw - 1.5rem));
  max-height: calc(100dvh - 1.5rem);
  overflow-y: auto;
  border-radius: 1rem;
  background: white;
  color: theme('colors.ink');
  box-shadow: theme('boxShadow.glass');
}
</style>
