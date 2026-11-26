/** 课表 API：上传意图/完成、我的课表、公开课表、对比、可见性。 */
import { request, requestForm } from './client'
import type {
  ScheduleCompareResult,
  AppointmentDetail, FixedMeetupInvite, MealInvite, CalendarEntry,
  ScheduleGroupDetail,
  ScheduleGroupJoinMode,
  ScheduleGroupSummary,
  ScheduleRecord,
  ScheduleSlot,
  ScheduleTiming,
  ScheduleUploadIntent,
  GroupAvailability,
} from '@/types'

export interface PdfSchedulePreview {
  suggested_name: string
  slots: ScheduleSlot[]
  warnings: string[]
}

/** PDF 课表预览：文件只在后端内存解析，不保存原文件。 */
export function previewSchedulePdf(file: File) {
  const form = new FormData()
  form.append('file', file)
  return requestForm<PdfSchedulePreview>('/schedule/pdf-preview', form)
}

export function getMealNotices() {
  return request<{unread:number}>({ method:'GET', url:'/schedule/meal-notices' })
}
export function markMealRead(id: string) {
  return request<AppointmentDetail>({method:'POST', url:`/schedule/appointments/${id}/read`})
}

export function getAppointments() {
  return request<{ items: AppointmentDetail[] }>({ method: 'GET', url: '/schedule/appointments' })
}

export function getCalendar() {
  return request<{items: CalendarEntry[]}>({ method: 'GET', url: '/schedule/calendar' })
}
export function saveCalendarEntry(id: string | null, data: Omit<CalendarEntry, 'id' | 'appointment_id'>) {
  return request<CalendarEntry>({ method: id ? 'PUT' : 'POST', url: id ? `/schedule/calendar/${id}` : '/schedule/calendar', data })
}
export function deleteCalendarEntry(id: string) {
  return request({ method: 'DELETE', url: `/schedule/calendar/${id}` })
}
export function createAppointment(data: MealInvite) {
  return request<AppointmentDetail>({ method: 'POST', url: '/schedule/appointments', data })
}

export function createFixedAppointment(data: FixedMeetupInvite) {
  return request<AppointmentDetail>({ method: 'POST', url: '/schedule/appointments/fixed', data })
}

export function getGroupAvailability(groupId: string, week: number, member_ids: string[]) {
  return request<GroupAvailability>({ method: 'POST', url: `/schedule/groups/${groupId}/availability`, data: { week, member_ids } })
}

export function createGroupAppointment(groupId: string, data: { week: number; member_ids: string[]; weekday: number; lesson_start: number; title: string; location?: string }) {
  return request<AppointmentDetail>({ method: 'POST', url: `/schedule/groups/${groupId}/appointments`, data })
}

export function getAppointment(appointmentId: string) {
  return request<AppointmentDetail>({ method: 'GET', url: `/schedule/appointments/${appointmentId}` })
}

export function respondAppointment(appointmentId: string, accepted: boolean, schedule_id?: string) {
  return request<AppointmentDetail>({
    method: 'POST', url: `/schedule/appointments/${appointmentId}/response`, data: { accepted, schedule_id },
  })
}

export function chooseAppointmentTimes(appointmentId: string, candidateIds: string[]) {
  return request<AppointmentDetail>({
    method: 'POST', url: `/schedule/appointments/${appointmentId}/choices`, data: { candidate_ids: candidateIds },
  })
}

export function confirmAppointment(appointmentId: string, candidateId: string) {
  return request<AppointmentDetail>({
    method: 'POST', url: `/schedule/appointments/${appointmentId}/confirm`, data: { candidate_id: candidateId },
  })
}

export function cancelAppointment(appointmentId: string) {
  return request<AppointmentDetail>({ method: 'POST', url: `/schedule/appointments/${appointmentId}/cancel` })
}

export function getMySchedules() {
  return request<{ items: ScheduleRecord[] }>({ method: 'GET', url: '/schedule/mine' })
}

export function createScheduleUploadIntent(filename: string, sizeBytes: number) {
  return request<ScheduleUploadIntent>({
    method: 'POST',
    url: '/schedule/upload-intent',
    data: { filename, size_bytes: sizeBytes },
  })
}

export function completeScheduleUpload(
  intent: ScheduleUploadIntent,
  originalName: string,
) {
  return request<ScheduleRecord>({
    method: 'POST',
    url: '/schedule/upload-complete',
    data: {
      bucket: intent.bucket,
      object_key: intent.object_key,
      original_name: originalName,
    },
  })
}

export function getSharedSchedule(username: string) {
  return request<ScheduleRecord>({
    method: 'GET',
    url: `/schedule/shared/${encodeURIComponent(username)}`,
  })
}

export function createManualSchedule(name: string, slots?: ScheduleSlot[], timing?: ScheduleTiming) {
  return request<ScheduleRecord>({ method: 'POST', url: '/schedule/manual', data: { name, slots, timing } })
}

/** 课表架：重命名课表，或存档/恢复到历史列表。 */
export function updateScheduleMeta(scheduleId: string, data: { original_name?: string; is_archived?: boolean }) {
  return request<ScheduleRecord>({
    method: 'PATCH', url: `/schedule/${scheduleId}`, data,
  })
}

/** 课表架拖动排序：提交本人全部课表的完整顺序。 */
export function saveScheduleOrder(ids: string[]) {
  return request<{ items: ScheduleRecord[] }>({
    method: 'PUT', url: '/schedule/order', data: { ids },
  })
}

export function saveScheduleSlots(scheduleId: string, slots: ScheduleSlot[], revision: number) {
  return request<ScheduleRecord>({
    method: 'PUT', url: `/schedule/${scheduleId}/slots`, data: { slots, revision },
  })
}

export function saveScheduleTiming(scheduleId: string, timing: ScheduleTiming, revision: number) {
  return request<ScheduleRecord>({
    method: 'PUT', url: `/schedule/${scheduleId}/timing`, data: { timing, revision },
  })
}

export function compareSchedules(slotsA: ScheduleSlot[], slotsB: ScheduleSlot[], week: number | null = null) {
  return request<ScheduleCompareResult>({
    method: 'POST',
    url: '/schedule/compare',
    data: { slots_a: slotsA, slots_b: slotsB, week },
  })
}

export function setScheduleVisibility(scheduleId: string, isPublic: boolean) {
  return request<ScheduleRecord>({
    method: 'PATCH',
    url: `/schedule/${scheduleId}/visibility`,
    data: { is_public: isPublic },
  })
}

export function deleteSchedule(scheduleId: string) {
  return request<{ message: string }>({
    method: 'DELETE',
    url: `/schedule/${scheduleId}`,
  })
}

// ---------- 课表对比群组 ----------
export function getScheduleGroups() {
  return request<{ items: ScheduleGroupSummary[] }>({ method: 'GET', url: '/schedule/groups' })
}

export function createScheduleGroup(name: string, joinMode: ScheduleGroupJoinMode = 'open') {
  return request<ScheduleGroupSummary>({
    method: 'POST', url: '/schedule/groups', data: { name, join_mode: joinMode },
  })
}

export function joinScheduleGroup(code: string) {
  return request<ScheduleGroupSummary>({
    method: 'POST', url: '/schedule/groups/join', data: { code },
  })
}

export function getScheduleGroup(groupId: string, week: number | null = null) {
  return request<ScheduleGroupDetail>({
    method: 'GET',
    url: `/schedule/groups/${groupId}`,
    params: week === null ? {} : { week },
  })
}

export function updateScheduleGroup(
  groupId: string,
  data: { name?: string; join_mode?: ScheduleGroupJoinMode },
) {
  return request<ScheduleGroupSummary>({
    method: 'PATCH', url: `/schedule/groups/${groupId}`, data,
  })
}

export function deleteScheduleGroup(groupId: string) {
  return request<{ message: string }>({
    method: 'DELETE', url: `/schedule/groups/${groupId}`,
  })
}

export function setScheduleGroupSchedule(groupId: string, scheduleId: string | null) {
  return request<ScheduleGroupSummary>({
    method: 'PUT', url: `/schedule/groups/${groupId}/schedule`, data: { schedule_id: scheduleId },
  })
}

export function approveScheduleGroupMember(groupId: string, memberUserId: string) {
  return request<ScheduleGroupSummary>({
    method: 'POST', url: `/schedule/groups/${groupId}/members/${memberUserId}/approve`,
  })
}

export function rejectScheduleGroupMember(groupId: string, memberUserId: string) {
  return request<{ message: string }>({
    method: 'POST', url: `/schedule/groups/${groupId}/members/${memberUserId}/reject`,
  })
}

export function removeScheduleGroupMember(groupId: string, memberUserId: string) {
  return request<{ message: string }>({
    method: 'DELETE', url: `/schedule/groups/${groupId}/members/${memberUserId}`,
  })
}
