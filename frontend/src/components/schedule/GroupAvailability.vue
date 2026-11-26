<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { createGroupAppointment, getGroupAvailability } from '@/api/schedule'
import type { AppointmentDetail, GroupAvailability, ScheduleGroupMember } from '@/types'

const props = defineProps<{ groupId: string; members: ScheduleGroupMember[]; week: number | null; myScheduleId: string | null; inviteEnabled: boolean }>()
const emit = defineEmits<{ created: [appointment: AppointmentDetail] }>()
const selected = ref<string[]>([])
const manualWeek = ref(1)
const effectiveWeek = computed(() => props.week ?? manualWeek.value)
const availability = ref<GroupAvailability | null>(null)
const chosen = ref<GroupAvailability['slots'][number] | null>(null)
const title = ref('群组约定')
const location = ref('')
const busy = ref(false)
const error = ref('')
const days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
const candidates = computed(() => props.members.filter(m => !m.is_me && m.schedule_id))
const slotsByDay = computed(() => days.map((day, weekday) => ({ day, slots: availability.value?.slots.filter(slot => slot.weekday === weekday) ?? [] })).filter(day => day.slots.length))

watch(() => [props.groupId, props.week, props.myScheduleId, props.members.map(m => `${m.user_id}:${m.schedule_id}`).join('|')], () => {
  selected.value = selected.value.filter(id => candidates.value.some(member => member.user_id === id))
  availability.value = null
  chosen.value = null
})
watch(selected, () => { availability.value = null; chosen.value = null }, { deep: true })
watch(manualWeek, () => { availability.value = null; chosen.value = null })

async function search() {
  if (!selected.value.length || busy.value) return
  busy.value = true; error.value = ''; chosen.value = null
  const groupId = props.groupId
  const week = effectiveWeek.value
  const memberIds = [...selected.value]
  try {
    const result = await getGroupAvailability(groupId, week, memberIds)
    if (groupId === props.groupId && week === effectiveWeek.value && memberIds.join(',') === selected.value.join(',')) availability.value = result
  }
  catch (e) { availability.value = null; error.value = e instanceof Error ? e.message : '查询失败' }
  finally { busy.value = false }
}
async function invite() {
  if (!chosen.value || !title.value.trim() || busy.value) return
  busy.value = true; error.value = ''
  try {
    const result = await createGroupAppointment(props.groupId, { week: effectiveWeek.value, member_ids: selected.value, weekday: chosen.value.weekday, lesson_start: chosen.value.lesson, title: title.value.trim(), location: location.value.trim() || undefined })
    availability.value = null; chosen.value = null
    emit('created', result)
  } catch (e) { error.value = e instanceof Error ? e.message : '邀请发送失败' }
  finally { busy.value = false }
}
function clock(iso: string) { return new Intl.DateTimeFormat('zh-CN', { timeZone: 'Asia/Shanghai', hour: '2-digit', minute: '2-digit', hour12: false }).format(new Date(iso)) }
</script>

<template>
  <section class="mt-6 border-t border-primary-100 pt-5">
    <h3 class="text-base font-semibold text-ink">多人共同空闲</h3>
    <p v-if="!myScheduleId" class="mt-2 text-sm text-sub">请先共享你的课表。</p>
    <p v-else-if="!candidates.length" class="mt-2 text-sm text-sub">其他成员共享课表后即可一起查询。</p>
    <template v-else>
      <fieldset class="mt-3 flex flex-wrap gap-2" :disabled="busy"><legend class="mb-2 text-sm text-sub">选择成员（最多 9 人）</legend>
        <label v-for="member in candidates" :key="member.user_id" class="flex items-center gap-2 rounded-md border border-primary-100 bg-white px-3 py-2 text-sm text-ink">
          <input v-model="selected" type="checkbox" :value="member.user_id" :disabled="selected.length >= 9 && !selected.includes(member.user_id)" class="accent-primary" />{{ member.display_name }}
        </label>
      </fieldset>
      <label v-if="!week" class="mt-3 block text-sm text-sub">查询周次<select v-model="manualWeek" class="input mt-1 block w-auto" :disabled="busy"><option v-for="n in 53" :key="n" :value="n">第 {{ n }} 周</option></select></label>
      <button class="btn-sm mt-3" :disabled="busy || !selected.length || !myScheduleId" @click="search">{{ busy ? '查询中…' : '查询共同空闲' }}</button>
      <p v-if="error" role="alert" class="mt-3 text-sm text-red-600">{{ error }}</p>
      <template v-if="availability">
        <p class="mt-4 text-sm text-sub">{{ availability.member_count }} 人 · 第 {{ availability.week }} 周</p>
        <p v-if="!availability.slots.length" class="mt-3 text-sm text-sub">本周没有可用的共同空闲时段。</p>
        <div v-else class="mt-3 space-y-3">
          <div v-for="day in slotsByDay" :key="day.day" class="flex flex-wrap items-center gap-2"><span class="w-10 text-sm text-sub">{{ day.day }}</span>
            <button v-for="slot in day.slots" :key="slot.starts_at" type="button" class="rounded-md border px-2.5 py-2 text-xs" :class="chosen?.starts_at === slot.starts_at ? 'border-primary bg-primary/15 text-primary-800' : 'border-primary-100 bg-white text-sub'" :aria-pressed="chosen?.starts_at === slot.starts_at" @click="chosen = slot">第 {{ slot.lesson }} 节 {{ clock(slot.starts_at) }}–{{ clock(slot.ends_at) }}</button>
          </div>
        </div>
        <form v-if="chosen && inviteEnabled" class="mt-4 grid gap-3 border-t border-primary-100 pt-4 sm:grid-cols-2" @submit.prevent="invite">
          <label class="text-sm text-sub">约定名称<input v-model="title" class="input mt-1 w-full" maxlength="128" required /></label>
          <label class="text-sm text-sub">地点（可选）<input v-model="location" class="input mt-1 w-full" maxlength="255" /></label>
          <div class="sm:col-span-2"><button type="submit" class="btn-primary" :disabled="busy || !title.trim()">{{ busy ? '发送中…' : '发起群组邀约' }}</button></div>
        </form>
      </template>
    </template>
  </section>
</template>
