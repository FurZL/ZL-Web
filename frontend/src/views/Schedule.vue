<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useDialog } from '@/composables/useDialog'
import { fetchSiteConfig, useSiteConfig } from '@/composables/useSiteConfig'
import Step1Upload from '@/components/schedule/Step1Upload.vue'
import Step2Partner from '@/components/schedule/Step2Partner.vue'
import Step3Result from '@/components/schedule/Step3Result.vue'
import CalendarAgenda from '@/components/schedule/CalendarAgenda.vue'
import ScheduleInvitationDialog from '@/components/schedule/ScheduleInvitationDialog.vue'
import ScheduleSlotEditor from '@/components/schedule/ScheduleSlotEditor.vue'
import ScheduleImportDialog from '@/components/schedule/ScheduleImportDialog.vue'
import ScheduleGroupPanel from '@/components/schedule/ScheduleGroupPanel.vue'
import { DAYS, appendSchedulePeriod, normalizeScheduleTiming, scheduleWeeks } from '@/components/schedule/calendar'
import ScheduleTimingEditor from '@/components/schedule/ScheduleTimingEditor.vue'
import {
  compareSchedules,
  cancelAppointment,
  createFixedAppointment,
  createManualSchedule,
  saveScheduleOrder,
  saveScheduleSlots, saveScheduleTiming,
  completeScheduleUpload,
  createScheduleUploadIntent,
  deleteSchedule,
  getAppointments, getCalendar, getAppointment,
  getMySchedules,
  getSharedSchedule,
  previewSchedulePdf,
  respondAppointment,
  setScheduleVisibility,
  updateScheduleMeta,
} from '@/api/schedule'
import type { CalendarEntry, AppointmentDetail, CompareFreeSlot, ScheduleCompareResult, ScheduleGroupMember, ScheduleRecord, ScheduleSlot, ScheduleTiming } from '@/types'

const step = ref(1)
const { showToast, showConfirm } = useDialog()
const { scheduleConfig } = useSiteConfig()

// ---------- 我的课表 ----------
const mySchedules = ref<ScheduleRecord[]>([])
const activeSchedule = ref<ScheduleRecord | null>(null)
const loadingMine = ref(true)
const browserScheduleImport = ref<{ id: string; schedule: { name: string; slots: ScheduleSlot[] } } | null>(null)
const browserScheduleImportSaving = ref(false)
const browserScheduleImportError = ref('')

function normalizeSchedule(schedule: ScheduleRecord): ScheduleRecord {
  return { ...schedule, timing: normalizeScheduleTiming(schedule.timing) }
}

function scheduleLessonCount(schedule: ScheduleRecord) {
  return normalizeScheduleTiming(schedule.timing).periods.length
}

function usedLessonCount(schedule: ScheduleRecord) {
  return Math.max((schedule.slots ?? []).reduce((max, slot) => Math.max(max, slot.lesson_end), 0), 0)
}

async function loadMine() {
  loadingMine.value = true
  try {
    const data = await getMySchedules()
    const schedules = data.items.map(normalizeSchedule)
    mySchedules.value = schedules
    const firstCurrent = schedules.find(item => !item.is_archived) ?? null
    if (activeSchedule.value) {
      const fresh = schedules.find(item => item.id === activeSchedule.value!.id)
      activeSchedule.value = fresh && !fresh.is_archived ? fresh : firstCurrent
    } else {
      activeSchedule.value = firstCurrent
    }
  } catch (e) {
    showToast(e instanceof Error ? e.message : '课表加载失败')
  } finally {
    loadingMine.value = false
  }
}

function validBrowserImport(value: unknown) {
  if (!value || typeof value !== 'object') return null
  const pending = value as { id?: unknown; targetOrigin?: unknown; schedule?: { name?: unknown; slots?: unknown } }
  if (typeof pending.id !== 'string' || pending.id.length > 64 || pending.targetOrigin !== window.location.origin) return null
  const schedule = pending.schedule
  if (!schedule || typeof schedule.name !== 'string' || !Array.isArray(schedule.slots)
    || !schedule.slots.length || schedule.slots.length > 500) return null
  const slots: ScheduleSlot[] = []
  for (const candidate of schedule.slots) {
    if (!candidate || typeof candidate !== 'object') return null
    const slot = candidate as Partial<ScheduleSlot>
    if (typeof slot.name !== 'string' || !slot.name.trim() || slot.name.length > 255
      || !Number.isInteger(slot.weekday) || slot.weekday! < 0 || slot.weekday! > 6
      || !Number.isInteger(slot.lesson_start) || slot.lesson_start! < 1 || slot.lesson_start! > 24
      || !Number.isInteger(slot.lesson_end) || slot.lesson_end! < slot.lesson_start! || slot.lesson_end! > 24
      || !Array.isArray(slot.weeks) || !slot.weeks.length || slot.weeks.length > 53
      || !slot.weeks.every((week) => Number.isInteger(week) && week >= 1 && week <= 53)) return null
    slots.push({
      kind: 'course',
      name: slot.name.trim(),
      location: typeof slot.location === 'string' ? slot.location.slice(0, 255) : '',
      campus: typeof slot.campus === 'string' ? slot.campus.slice(0, 128) : null,
      weekday: slot.weekday!,
      lesson_start: slot.lesson_start!,
      lesson_end: slot.lesson_end!,
      weeks: [...new Set(slot.weeks)].sort((a, b) => a - b),
    })
  }
  return { id: pending.id, schedule: { name: schedule.name.slice(0, 255), slots } }
}

function onScheduleExtensionMessage(event: MessageEvent) {
  if (event.source !== window || event.origin !== window.location.origin) return
  const message = event.data
  if (message?.source !== 'furzl-schedule-extension' || message.type !== 'SCHEDULE_IMPORT') return
  const imported = validBrowserImport(message.payload)
  if (!imported || browserScheduleImport.value?.id === imported.id) return
  browserScheduleImport.value = imported
  browserScheduleImportError.value = ''
}

function acknowledgeBrowserImport(importId: string) {
  window.postMessage({ source: 'furzl-schedule-page', type: 'ACK_IMPORT', id: importId }, window.location.origin)
}

onMounted(() => {
  void fetchSiteConfig(true)
  void loadMine()
  window.addEventListener('message', onScheduleExtensionMessage)
  window.postMessage({ source: 'furzl-schedule-page', type: 'READY' }, window.location.origin)
})
onUnmounted(() => window.removeEventListener('message', onScheduleExtensionMessage))

// ---------- 课表内的约定邀请 ----------
const appointments = ref<AppointmentDetail[]>([])
const appointmentLoading = ref(true)
const appointmentWorking = ref(false)
const appointmentError = ref('')
const selectedInvitation = ref<AppointmentDetail | null>(null)
const invitationError = ref('')
const gridInvitations = computed(() => appointments.value.filter(item => (
  item.mode === 'fixed'
  && item.status === 'pending'
  && item.viewer_participant.role === 'invitee'
  && item.viewer_participant.status === 'invited'
  && !item.is_group
)))
const groupInvitations = computed(() => appointments.value.filter(item => item.is_group && ['pending', 'confirmed'].includes(item.status)))
const invitationSchedules = computed(() => mySchedules.value.filter(item => !item.is_archived))

const calendarEntries = ref<CalendarEntry[]>([])
let generation = 0
async function loadAppointments() {
  const version = ++generation
  appointmentLoading.value = true
  try {
    const [meals, calendar] = await Promise.all([getAppointments(), getCalendar()])
    if (version !== generation) return
    const newlyConfirmed = meals.items.find(m => m.status === 'confirmed' && appointments.value.some(old => old.id===m.id && old.status !== 'confirmed'))
    if (newlyConfirmed) showToast(newlyConfirmed.title + '已约定，已加入我的日程')
    appointments.value = meals.items
    calendarEntries.value = calendar.items
    window.dispatchEvent(new CustomEvent('schedule-notices-changed'))
  } catch (error) {
    appointmentError.value = error instanceof Error ? error.message : '邀请加载失败'
  } finally {
    appointmentLoading.value = false
  }
}

let poll: ReturnType<typeof setInterval>
function refreshVisible() {
  if (!document.hidden && !appointmentWorking.value && !appointmentLoading.value) void loadAppointments()
}
onMounted(() => {
  void loadAppointments()
  poll = setInterval(refreshVisible, 30000)
  window.addEventListener('focus', refreshVisible)
})
onUnmounted(() => { clearInterval(poll); window.removeEventListener('focus', refreshVisible) })

function replaceAppointment(updated: AppointmentDetail) {
  const index = appointments.value.findIndex(item => item.id === updated.id)
  if (index === -1) appointments.value.unshift(updated)
  else appointments.value[index] = updated
}

function openInvitation(id: string) {
  selectedInvitation.value = appointments.value.find(item => item.id === id) ?? null
  invitationError.value = ''
}

async function respondInvitation(id: string, accepted: boolean, scheduleId?: string) {
  if (appointmentWorking.value) return
  appointmentWorking.value = true
  invitationError.value = ''
  try {
    const updated = await respondAppointment(id, accepted, scheduleId)
    ++generation
    replaceAppointment(updated)
    selectedInvitation.value = updated
    showToast(updated.status === 'confirmed' ? '约定已确认，已加入参与者日程' : accepted ? '已接受，等待其他成员回应' : '已婉拒这次约定')
    await loadAppointments()
    if (updated.status !== 'pending') selectedInvitation.value = null
  } catch (error) {
    invitationError.value = error instanceof Error ? error.message : '处理约定失败'
  } finally {
    appointmentWorking.value = false
  }
}

async function cancelInvitation(id: string) {
  if (!(await showConfirm('取消这次约定后，参与者已写入的日程也会移除。确定继续吗？'))) return
  if (appointmentWorking.value) return
  appointmentWorking.value = true
  invitationError.value = ''
  try {
    const updated = await cancelAppointment(id)
    ++generation
    replaceAppointment(updated)
    selectedInvitation.value = null
    showToast('约定已取消')
    await loadAppointments()
  } catch (error) {
    invitationError.value = error instanceof Error ? error.message : '取消约定失败'
  } finally {
    appointmentWorking.value = false
  }
}

const creating = ref(false)
const saving = ref(false)
const editError = ref('')
const editing = ref<{ schedule: ScheduleRecord; index: number | null; initial: ScheduleSlot } | null>(null)
const timingEditing = ref<ScheduleRecord | null>(null)
const timingSaving = ref(false)
const timingError = ref('')
const timingAdding = ref(false)
const slotMoving = ref(false)
const metaSaving = ref(false)

/** 后端返回的整份课表统一落到列表与当前课表，避免两处 revision 漂移。 */
function applyScheduleUpdate(updated: ScheduleRecord) {
  const normalized = normalizeSchedule(updated)
  mySchedules.value = mySchedules.value.map(item => item.id === normalized.id ? normalized : item)
  if (activeSchedule.value?.id === normalized.id) activeSchedule.value = normalized
  result.value = null
  return normalized
}

async function createBlank(name: string) {
  if (creating.value) return
  creating.value = true
  try {
    const record = await createManualSchedule(name)
    mySchedules.value.unshift(record)
    activeSchedule.value = record
  } catch (error) {
    showToast(error instanceof Error ? error.message : '创建失败')
  } finally { creating.value = false }
}

function closeBrowserImport() {
  const current = browserScheduleImport.value
  if (!current || browserScheduleImportSaving.value) return
  acknowledgeBrowserImport(current.id)
  browserScheduleImport.value = null
  browserScheduleImportError.value = ''
}

async function saveBrowserImport(value: { importId: string; name: string; slots: ScheduleSlot[]; timing: ScheduleTiming }) {
  const current = browserScheduleImport.value
  if (!current || current.id !== value.importId || browserScheduleImportSaving.value) return
  browserScheduleImportSaving.value = true
  browserScheduleImportError.value = ''
  try {
    const created = normalizeSchedule(await createManualSchedule(value.name, value.slots, value.timing))
    mySchedules.value = [created, ...mySchedules.value.filter((schedule) => schedule.id !== created.id)]
    activeSchedule.value = created
    result.value = null
    step.value = 1
    acknowledgeBrowserImport(current.id)
    browserScheduleImport.value = null
    showToast('教务课表已导入，当前为仅自己可见')
  } catch (error) {
    browserScheduleImportError.value = error instanceof Error ? error.message : '课表导入失败，请重试'
  } finally {
    browserScheduleImportSaving.value = false
  }
}

function openEditor(index: number | null, weekday: number, lesson: number, week: number | null) {
  const schedule = activeSchedule.value
  if (!schedule || slotMoving.value) return
  const initial: ScheduleSlot = index === null ? {
    kind: 'event', name: '', location: '', campus: null, weekday,
    lesson_start: lesson, lesson_end: lesson, weeks: week === null ? [] : [week],
  } : { kind: 'course', ...schedule.slots[index] }
  editing.value = { schedule, index, initial: { ...initial, weeks: [...initial.weeks] } }
  editError.value = ''
}

async function persistEdit(slot: ScheduleSlot | null) {
  const context = editing.value
  if (!context || saving.value) return
  const slots = [...context.schedule.slots]
  if (context.index === null) {
    if (!slot) return
    slots.push(slot)
  } else if (slot) slots[context.index] = slot
  else slots.splice(context.index, 1)
  saving.value = true
  editError.value = ''
  try {
    applyScheduleUpdate(await saveScheduleSlots(context.schedule.id, slots, context.schedule.revision))
    editing.value = null
    showToast(slot ? '已保存，日程会参与忙闲计算' : '已删除')
  } catch (error) {
    editError.value = error instanceof Error ? error.message : '保存失败，请重试'
  } finally { saving.value = false }
}

function openTimingEditor() {
  if (!activeSchedule.value) return
  const schedule = normalizeSchedule(activeSchedule.value)
  activeSchedule.value = schedule
  mySchedules.value = mySchedules.value.map(item => item.id === schedule.id ? schedule : item)
  timingEditing.value = schedule
  timingError.value = ''
}

async function persistTiming(timing: ScheduleTiming) {
  const schedule = timingEditing.value
  if (!schedule || timingSaving.value) return
  timingSaving.value = true
  timingError.value = ''
  try {
    applyScheduleUpdate(await saveScheduleTiming(schedule.id, timing, schedule.revision))
    timingEditing.value = null
    showToast('作息已保存，课表与约饭会使用新时间')
  } catch (error) {
    timingError.value = error instanceof Error ? error.message : '作息保存失败，请重试'
  } finally { timingSaving.value = false }
}

/** 网格底部“添加一节”：按当前作息规则追加，并沿用 revision 校验。 */
async function addGridLesson() {
  const schedule = activeSchedule.value
  if (!schedule || timingAdding.value || slotMoving.value) return
  const nextTiming = appendSchedulePeriod(normalizeScheduleTiming(schedule.timing))
  if (!nextTiming) {
    showToast('当天剩余时间不足，无法再加一节')
    return
  }
  timingAdding.value = true
  try {
    applyScheduleUpdate(await saveScheduleTiming(schedule.id, nextTiming, schedule.revision))
    const added = nextTiming.periods[nextTiming.periods.length - 1]
    showToast(`已添加第 ${nextTiming.periods.length} 节 ${added[0]}–${added[1]}`)
  } catch (error) {
    showToast(error instanceof Error ? error.message : '添加节次失败，请重试')
  } finally { timingAdding.value = false }
}

/** 拖动课程/日程或拉伸结束节次后保存；先乐观更新，失败回滚并提示。 */
async function moveSlot(index: number, weekday: number, lessonStart: number, lessonEnd: number) {
  const schedule = activeSchedule.value
  if (!schedule || slotMoving.value || timingAdding.value) return
  const existing = schedule.slots[index]
  if (!existing) return
  if (existing.weekday === weekday && existing.lesson_start === lessonStart && existing.lesson_end === lessonEnd) return
  const slots = schedule.slots.map((slot, i) => (i === index
    ? { ...slot, weekday, lesson_start: lessonStart, lesson_end: lessonEnd }
    : slot))
  const previous = schedule
  const optimistic: ScheduleRecord = { ...schedule, slots }
  activeSchedule.value = optimistic
  mySchedules.value = mySchedules.value.map(item => item.id === schedule.id ? optimistic : item)
  slotMoving.value = true
  try {
    applyScheduleUpdate(await saveScheduleSlots(schedule.id, slots, schedule.revision))
    const range = lessonStart === lessonEnd ? `第 ${lessonStart} 节` : `第 ${lessonStart}–${lessonEnd} 节`
    showToast(`已更新到${DAYS[weekday]}${range}`)
  } catch (error) {
    if (activeSchedule.value?.id === schedule.id) activeSchedule.value = previous
    mySchedules.value = mySchedules.value.map(item => item.id === schedule.id ? previous : item)
    showToast(error instanceof Error ? error.message : '移动失败，请重试')
  } finally { slotMoving.value = false }
}

// ---------- 课表架：命名与存档 ----------
async function renameSchedule(schedule: ScheduleRecord, name: string) {
  const trimmed = name.trim()
  if (!trimmed || metaSaving.value) return
  if (trimmed === (schedule.original_name ?? '')) return
  metaSaving.value = true
  try {
    applyScheduleUpdate(await updateScheduleMeta(schedule.id, { original_name: trimmed }))
    showToast('课表已命名')
  } catch (error) {
    showToast(error instanceof Error ? error.message : '命名失败，请重试')
  } finally { metaSaving.value = false }
}

async function archiveSchedule(schedule: ScheduleRecord) {
  if (metaSaving.value) return
  metaSaving.value = true
  try {
    applyScheduleUpdate(await updateScheduleMeta(schedule.id, { is_archived: true }))
    if (activeSchedule.value?.id === schedule.id) {
      activeSchedule.value = mySchedules.value.find(item => !item.is_archived) ?? null
    }
    showToast('已存档到历史课表，可随时恢复')
  } catch (error) {
    showToast(error instanceof Error ? error.message : '存档失败，请重试')
  } finally { metaSaving.value = false }
}

async function restoreSchedule(schedule: ScheduleRecord) {
  if (metaSaving.value) return
  metaSaving.value = true
  try {
    applyScheduleUpdate(await updateScheduleMeta(schedule.id, { is_archived: false }))
    showToast('已恢复到课表架')
  } catch (error) {
    showToast(error instanceof Error ? error.message : '恢复失败，请重试')
  } finally { metaSaving.value = false }
}

async function reorderSchedules(ids: string[]) {
  if (metaSaving.value) return
  metaSaving.value = true
  try {
    const data = await saveScheduleOrder(ids)
    mySchedules.value = data.items.map(normalizeSchedule)
    if (activeSchedule.value) {
      activeSchedule.value = mySchedules.value.find(item => item.id === activeSchedule.value!.id) ?? null
    }
    showToast('课表顺序已保存')
  } catch (error) {
    showToast(error instanceof Error ? error.message : '排序保存失败，正在重新加载')
    await loadMine()
  } finally { metaSaving.value = false }
}

// ---------- 上传 ----------
const uploading = ref(false)
const uploadError = ref('')
const pdfPreview = ref<{ name: string; slots: ScheduleSlot[]; warnings: string[] } | null>(null)
const pdfImportId = ref('')
const pdfSaving = ref(false)
const pdfError = ref('')

async function parsePdfFile(file: File) {
  if (uploading.value || pdfSaving.value) return
  uploading.value = true
  uploadError.value = ''
  try {
    const result = await previewSchedulePdf(file)
    pdfPreview.value = {
      name: result.suggested_name || 'PDF 导入课表',
      slots: result.slots,
      warnings: result.warnings ?? [],
    }
    pdfImportId.value = `pdf-${Date.now()}`
    pdfError.value = ''
  } catch (error) {
    uploadError.value = error instanceof Error ? error.message : 'PDF 解析失败，请改用 ICS / TXT'
  } finally {
    uploading.value = false
  }
}

function closePdfPreview() {
  if (pdfSaving.value) return
  pdfPreview.value = null
  pdfError.value = ''
}

async function savePdfImport(value: { importId: string; name: string; slots: ScheduleSlot[]; timing: ScheduleTiming }) {
  if (!pdfPreview.value || value.importId !== pdfImportId.value || pdfSaving.value) return
  pdfSaving.value = true
  pdfError.value = ''
  try {
    const created = normalizeSchedule(await createManualSchedule(value.name, value.slots, value.timing))
    mySchedules.value = [created, ...mySchedules.value.filter(s => s.id !== created.id)]
    activeSchedule.value = created
    pdfPreview.value = null
    result.value = null
    step.value = 1
    showToast(`已导入 ${value.slots.length} 条课程，默认仅自己可见`)
  } catch (error) {
    pdfError.value = error instanceof Error ? error.message : 'PDF 课表保存失败，请重试'
  } finally {
    pdfSaving.value = false
  }
}

async function uploadFile(f: File) {
  if (uploading.value) return
  const name = f.name.toLowerCase()
  if (name.endsWith('.pdf')) {
    await parsePdfFile(f)
    return
  }
  if (!name.endsWith('.ics') && !name.endsWith('.txt')) {
    uploadError.value = '仅支持 .ics / .txt / .pdf 文件'
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
    const normalized = normalizeSchedule(record)
    mySchedules.value = [normalized, ...mySchedules.value]
    activeSchedule.value = normalized
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
watch(partnerName, () => { partner.value = null; result.value = null })

async function searchPartner() {
  const q = partnerName.value.trim()
  if (!q || partnerSearching.value) return
  partnerSearching.value = true
  partnerError.value = ''
  partner.value = null
  try {
    const found = await getSharedSchedule(q)
    if (partnerName.value.trim() === q) partner.value = found
  } catch (e) {
    partnerError.value = e instanceof Error ? e.message : '未找到该用户公开的课表'
  } finally {
    partnerSearching.value = false
  }
}

// ---------- 对比结果 ----------
const comparing = ref(false)
const compareError = ref('')
const result = ref<ScheduleCompareResult | null>(null)
const compareWeek = ref<number | null>(null)
const activeGroupId = ref<string | null>(null)
const groupCompareLoading = ref(false)
let compareSequence = 0

async function runCompare(week: number | null = null) {
  if (!activeSchedule.value || !partner.value) return
  activeGroupId.value = null
  meetupInvite.value = null
  meetupError.value = ''
  comparing.value = true
  compareError.value = ''
  compareWeek.value = week
  result.value = null
  const sequence = ++compareSequence
  try {
    // 每次重新读取已保存课表，尊重圈友撤销公开及最新日程。
    const [mine, shared] = await Promise.all([getMySchedules(), getSharedSchedule(partner.value.owner!.username)])
    if (sequence !== compareSequence) return
    const current = mine.items.find(s => s.id === activeSchedule.value?.id)
    if (!current) throw new Error('当前课表已删除，请重新选择')
    activeSchedule.value = current
    mySchedules.value = mine.items
    partner.value = shared
    const compared = await compareSchedules(current.slots, shared.slots, week)
    if (sequence !== compareSequence) return
    result.value = compared
    step.value = 3
  } catch (e) {
    if (sequence !== compareSequence) return
    compareError.value = e instanceof Error ? e.message : '对比失败'
  } finally {
    if (sequence === compareSequence) comparing.value = false
  }
}

// ---------- 从比较结果发起固定时间约定 ----------
const meetupInvite = ref<AppointmentDetail | null>(null)
const meetupInviting = ref(false)
const meetupError = ref('')

async function inviteMeetup(payload: { free: CompareFreeSlot; week: number; title: string }) {
  if (!activeSchedule.value || !partner.value?.owner || meetupInviting.value) return
  meetupInviting.value = true
  meetupError.value = ''
  try {
    const created = await createFixedAppointment({
      schedule_id: activeSchedule.value.id,
      invitee_username: partner.value.owner.username,
      title: payload.title,
      week: payload.week,
      weekday: payload.free.weekday,
      lesson_start: payload.free.lesson_start,
      lesson_end: payload.free.lesson_end,
    })
    meetupInvite.value = created
    showToast('约定邀请已发送，对方同意后会加入双方日程')
  } catch (e) {
    meetupError.value = e instanceof Error ? e.message : '约定邀请发送失败'
  } finally {
    meetupInviting.value = false
  }
}

async function refreshMeetupInvite() {
  if (!meetupInvite.value) return
  try {
    const latest = await getAppointment(meetupInvite.value.id)
    meetupInvite.value = latest
    if (latest.status === 'confirmed') showToast('对方已同意，约定已加入双方日程')
  } catch (e) {
    meetupError.value = e instanceof Error ? e.message : '刷新约定状态失败'
  }
}

interface GroupComparePayload {
  groupId: string
  groupName: string
  member: ScheduleGroupMember
  week: number | null
  myScheduleId: string
}

async function compareGroupMember(payload: GroupComparePayload) {
  if (groupCompareLoading.value) return
  const mine = mySchedules.value.find((item) => item.id === payload.myScheduleId && !item.is_archived)
  if (!mine) {
    showToast('找不到共享给群组的课表，请重新选择共享课表')
    return
  }
  if (!payload.member.slots.length) {
    showToast('对方还没有共享可对比的课表')
    return
  }
  groupCompareLoading.value = true
  compareError.value = ''
  result.value = null
  try {
    const compared = await compareSchedules(mine.slots, payload.member.slots, payload.week)
    partner.value = {
      id: payload.member.schedule_id ?? `group-${payload.member.user_id}`,
      revision: 0,
      original_name: payload.member.schedule_name ?? `${payload.member.display_name}的课表`,
      format: 'group',
      slots: payload.member.slots,
      timing: normalizeScheduleTiming(payload.member.timing),
      is_public: false,
      is_archived: false,
      created_at: null,
      expires_at: null,
      owner: {
        id: payload.member.user_id,
        username: payload.member.username,
        display_name: payload.member.display_name,
      },
    }
    result.value = compared
    compareWeek.value = payload.week
    activeGroupId.value = payload.groupId
    activeSchedule.value = mine
    step.value = 3
  } catch (e) {
    showToast(e instanceof Error ? e.message : '群组对比失败')
  } finally {
    groupCompareLoading.value = false
  }
}
</script>

<template>
  <div class="mx-auto max-w-[1440px] px-4 py-8 sm:py-10">
    <div class="flex flex-wrap items-end justify-between gap-5">
      <div>
        <p class="text-xs font-semibold uppercase tracking-[0.2em] text-primary-500">Schedule studio</p>
        <h1 class="mt-2 text-3xl font-bold tracking-tight text-ink sm:text-4xl">找个课搭子一起上课</h1>
        <p class="mt-3 max-w-xl text-sm leading-6 text-sub">把课表变成一张可以一起看的时间地图，找到共同空闲，也许还能发现同一间教室的偶遇。</p>
      </div>
      <div class="hidden rounded-3xl border border-white/70 bg-white/45 px-5 py-4 text-right shadow-soft sm:block">
        <p class="text-xs text-faint">当前模式</p>
        <p class="mt-1 text-sm font-semibold text-primary-700">{{ step === 1 ? '我的课表' : step === 2 ? '寻找搭子' : '对比结果' }}</p>
      </div>
    </div>

    <!-- 步骤指示 -->
    <div class="mt-8 flex max-w-2xl items-center gap-2 text-sm">
      <template v-for="(label, i) in ['上传课表', '选择对象', '查看结果']" :key="label">
        <div class="flex shrink-0 items-center gap-2">
          <span
            class="flex h-8 w-8 items-center justify-center rounded-full text-xs font-semibold"
            :class="step > i ? 'bg-primary text-white' : step === i + 1 ? 'bg-primary-200 text-primary-800' : 'bg-white/70 text-faint border border-white/60'"
          >
            {{ i + 1 }}
          </span>
          <span class="hidden sm:inline" :class="step === i + 1 ? 'font-semibold text-ink' : 'text-faint'">{{ label }}</span>
        </div>
        <span v-if="i < 2" class="h-px min-w-6 flex-1 bg-primary-200 sm:min-w-12"></span>
      </template>
    </div>

    <!-- Step 1 -->
    <Step1Upload
      v-if="step === 1"
      :schedules="mySchedules"
      :active-schedule="activeSchedule"
      :loading="loadingMine"
      :creating="creating"
      :uploading="uploading"
      :upload-error="uploadError"
      :adding-lesson="timingAdding"
      :slot-moving="slotMoving"
      :meta-saving="metaSaving"
      :invitations="gridInvitations"
      :file-import-enabled="scheduleConfig.file_import_enabled"
      :public-share-enabled="scheduleConfig.public_share_enabled"
      @select="activeSchedule = $event"
      @toggle-share="toggleShare"
      @remove="removeSchedule"
      @upload="uploadFile"
      @create="createBlank"
      @edit="openEditor"
      @reload="loadMine"
      @clear-error="uploadError = ''"
      @timing="openTimingEditor"
      @next="step = 2"
      @move="moveSlot"
      @add-lesson="addGridLesson"
      @rename="renameSchedule"
      @archive="archiveSchedule"
      @restore="restoreSchedule"
      @reorder="reorderSchedules"
      @invitation="openInvitation"
    />
    <template v-if="step === 1">
    <CalendarAgenda :entries="calendarEntries" @refresh="loadAppointments" />
    <section v-if="groupInvitations.length" class="mt-5 border-t border-primary-100 pt-4">
      <h2 class="text-base font-semibold text-ink">群组邀约</h2>
      <button v-for="invitation in groupInvitations" :key="invitation.id" class="mt-2 flex w-full flex-wrap items-center justify-between gap-2 rounded-md border border-primary-100 bg-white px-4 py-3 text-left text-sm" @click="openInvitation(invitation.id)">
        <span class="font-medium text-ink">{{ invitation.title }}</span><span class="text-sub">{{ invitation.status === 'confirmed' ? '已确认' : invitation.viewer_participant.status === 'invited' ? '待你回应' : '等待成员回应' }} · {{ invitation.fixed ? new Date(invitation.fixed.starts_at).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' }) : '' }}</span>
      </button>
    </section>
    </template>

    <!-- Step 2 -->
    <template v-else-if="step === 2">
      <Step2Partner
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
      <ScheduleGroupPanel
        :join-enabled="scheduleConfig.group_join_enabled"
        :schedules="mySchedules"
        :initial-group-id="activeGroupId"
        :comparing="groupCompareLoading"
        :invite-enabled="scheduleConfig.fixed_invite_enabled"
        @compare="compareGroupMember"
        @created="(appointment) => { replaceAppointment(appointment); selectedInvitation = appointment; void loadAppointments() }"
      />
    </template>

    <!-- Step 3 -->
    <Step3Result
      v-else
      :my-schedule="activeSchedule"
      :partner="partner"
      :result="result"
      :week="compareWeek"
      :loading="comparing"
      :error="compareError"
      :invite="meetupInvite"
      :inviting="meetupInviting"
      :invite-error="meetupError"
      :invite-enabled="scheduleConfig.fixed_invite_enabled"
      @week="runCompare"
      @back="step = 2"
      @invite="inviteMeetup"
      @refresh-invite="refreshMeetupInvite"
    />
    <ScheduleInvitationDialog
      v-if="selectedInvitation"
      :invitation="selectedInvitation"
      :schedules="invitationSchedules"
      :active-schedule="activeSchedule"
      :saving="appointmentWorking"
      :error="invitationError"
      @close="!appointmentWorking && (selectedInvitation = null)"
      @respond="respondInvitation"
      @cancel="cancelInvitation"
    />
    <ScheduleSlotEditor v-if="editing" :initial="editing.initial" :editing="editing.index !== null"
      :saving="saving" :error="editError" :term-weeks="scheduleWeeks(editing.schedule.slots)"
      :max-lesson="scheduleLessonCount(editing.schedule)"
      @close="!saving && (editing = null)" @save="persistEdit" @remove="persistEdit(null)" />
    <ScheduleTimingEditor v-if="timingEditing" :initial="timingEditing.timing" :saving="timingSaving" :error="timingError"
      :used-lesson="usedLessonCount(timingEditing)"
      @close="!timingSaving && (timingEditing = null)" @save="persistTiming" />
    <ScheduleImportDialog v-if="browserScheduleImport"
      :import-id="browserScheduleImport.id"
      :initial-name="browserScheduleImport.schedule.name"
      :slots="browserScheduleImport.schedule.slots"
      :saving="browserScheduleImportSaving || loadingMine"
      :error="browserScheduleImportError"
      @close="closeBrowserImport"
      @save="saveBrowserImport" />
    <ScheduleImportDialog v-if="pdfPreview"
      :import-id="pdfImportId"
      :initial-name="pdfPreview.name"
      :slots="pdfPreview.slots"
      :title="'确认导入 PDF 课表'"
      :notices="pdfPreview.warnings"
      :saving="pdfSaving"
      :error="pdfError"
      @close="closePdfPreview"
      @save="savePdfImport" />
  </div>
</template>
