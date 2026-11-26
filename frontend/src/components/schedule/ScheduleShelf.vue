<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { ScheduleRecord } from '@/types'
import ScheduleMiniPreview from './ScheduleMiniPreview.vue'

const props = defineProps<{
  schedules: ScheduleRecord[]
  activeId: string | null
  creating: boolean
  busy: boolean
  fileImportEnabled: boolean
  publicShareEnabled: boolean
}>()

const emit = defineEmits<{
  select: [schedule: ScheduleRecord]
  create: [name: string]
  rename: [schedule: ScheduleRecord, name: string]
  archive: [schedule: ScheduleRecord]
  restore: [schedule: ScheduleRecord]
  toggleShare: [schedule: ScheduleRecord]
  remove: [schedule: ScheduleRecord]
  reorder: [ids: string[]]
}>()

interface ShelfDrag {
  id: string
  archived: boolean
  pointerId: number
  startX: number
  startY: number
  active: boolean
  moved: boolean
}

const drag = ref<ShelfDrag | null>(null)
const order = ref<string[]>([])
const shelfRoot = ref<HTMLElement | null>(null)
const newName = ref('我的学期课表')
const renamingId = ref<string | null>(null)
const renameDraft = ref('')
const renameError = ref('')
const showArchived = ref(true)

const scheduleMap = computed(() => new Map(props.schedules.map(item => [item.id, item])))
const currentSchedules = computed(() => order.value
  .map(id => scheduleMap.value.get(id))
  .filter((item): item is ScheduleRecord => Boolean(item && !item.is_archived)))
const archivedSchedules = computed(() => order.value
  .map(id => scheduleMap.value.get(id))
  .filter((item): item is ScheduleRecord => Boolean(item && item.is_archived)))

// 服务端顺序是排序基线；拖动期间不要用旧 props 覆盖正在本地重排的顺序。
watch(
  () => props.schedules.map(item => item.id),
  (ids) => {
    if (drag.value?.active) return
    order.value = ids
  },
  { immediate: true },
)

function formatLabel(schedule: ScheduleRecord) {
  if (schedule.format === 'manual') return '手工课表'
  return schedule.format ? schedule.format.toUpperCase() : '课表'
}

function dateLabel(schedule: ScheduleRecord) {
  return schedule.created_at ? schedule.created_at.slice(0, 10) : '日期未知'
}

function startRename(schedule: ScheduleRecord) {
  if (props.busy) return
  renamingId.value = schedule.id
  renameDraft.value = schedule.original_name ?? ''
  renameError.value = ''
}

function cancelRename() {
  renamingId.value = null
  renameError.value = ''
}

function submitRename(schedule: ScheduleRecord) {
  const name = renameDraft.value.trim()
  if (!name) {
    renameError.value = '课表名称不能为空'
    return
  }
  if (props.busy) return
  renamingId.value = null
  renameError.value = ''
  if (name !== (schedule.original_name ?? '')) emit('rename', schedule, name)
}

function create() {
  const name = newName.value.trim()
  if (!name || props.creating) return
  emit('create', name)
}

// ---------- 课表架拖动排序（同组内，鼠标/触控笔；方向键可移动） ----------
function groupIds(archived: boolean) {
  return order.value.filter(id => Boolean(scheduleMap.value.get(id)?.is_archived) === archived)
}

function moveWithinGroup(sourceId: string, targetId: string) {
  const source = scheduleMap.value.get(sourceId)
  const target = scheduleMap.value.get(targetId)
  if (!source || !target || source.is_archived !== target.is_archived) return
  const group = groupIds(source.is_archived)
  const from = group.indexOf(sourceId)
  const to = group.indexOf(targetId)
  if (from < 0 || to < 0 || from === to) return
  group.splice(to, 0, group.splice(from, 1)[0])
  let cursor = 0
  order.value = order.value.map((id) => (
    Boolean(scheduleMap.value.get(id)?.is_archived) === source.is_archived ? group[cursor++] : id
  ))
}

function reorderByKeyboard(schedule: ScheduleRecord, delta: number) {
  if (props.busy) return
  const group = groupIds(schedule.is_archived)
  const from = group.indexOf(schedule.id)
  const to = from + delta
  if (from < 0 || to < 0 || to >= group.length) return
  moveWithinGroup(schedule.id, group[to])
  emit('reorder', [...order.value])
}

function cardAtPoint(x: number, y: number) {
  const element = document.elementFromPoint(x, y)
  const card = element instanceof Element ? element.closest<HTMLElement>('[data-shelf-card]') : null
  return card?.dataset.scheduleId ?? null
}

function detachDragListeners() {
  window.removeEventListener('pointermove', onDragMove)
  window.removeEventListener('pointerup', onDragEnd)
  window.removeEventListener('pointercancel', onDragCancel)
}

function startDrag(event: PointerEvent, schedule: ScheduleRecord) {
  if (props.busy || props.creating || event.button !== 0 || event.pointerType === 'touch') return
  drag.value = {
    id: schedule.id,
    archived: schedule.is_archived,
    pointerId: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
    active: false,
    moved: false,
  }
  window.addEventListener('pointermove', onDragMove)
  window.addEventListener('pointerup', onDragEnd)
  window.addEventListener('pointercancel', onDragCancel)
}

function onDragMove(event: PointerEvent) {
  const state = drag.value
  if (!state || event.pointerId !== state.pointerId) return
  if (!state.active) {
    if (Math.hypot(event.clientX - state.startX, event.clientY - state.startY) < 4) return
    state.active = true
    document.body.classList.add('shelf-dragging')
  }
  const targetId = cardAtPoint(event.clientX, event.clientY)
  if (!targetId || targetId === state.id) return
  moveWithinGroup(state.id, targetId)
  state.moved = true
}

function endDrag(event: PointerEvent, commit: boolean) {
  const state = drag.value
  detachDragListeners()
  document.body.classList.remove('shelf-dragging')
  drag.value = null
  if (!state || event.pointerId !== state.pointerId || !state.active) return
  if (commit && state.moved) emit('reorder', [...order.value])
}

function onDragEnd(event: PointerEvent) {
  endDrag(event, true)
}

function onDragCancel(event: PointerEvent) {
  endDrag(event, false)
}
</script>

<template>
  <section ref="shelfRoot" class="mt-6">
    <div class="flex flex-wrap items-end justify-between gap-3">
      <div>
        <p class="text-xs font-semibold uppercase tracking-[0.18em] text-primary-500">Schedule shelf</p>
        <h3 class="mt-1 flex items-center gap-2 text-lg font-bold text-ink">
          课表架
          <span class="tag-badge-sm">{{ schedules.length }}</span>
        </h3>
        <p class="mt-1 max-w-xl text-xs leading-5 text-sub">
          给每学期的课表起个名字；旧课表可以存档到历史，随时恢复，不会丢失课程和作息。拖动卡片或右上角把手可以调整顺序。
        </p>
      </div>
      <form class="flex w-full max-w-sm gap-2 sm:w-auto" @submit.prevent="create">
        <label class="sr-only" for="shelf-new-name">新课表名称</label>
        <input
          id="shelf-new-name"
          v-model="newName"
          class="input !w-40 !py-1.5 text-sm"
          maxlength="255"
          placeholder="新课表名称"
          :disabled="creating"
        />
        <button type="submit" class="btn-sm-primary shrink-0" :disabled="creating || !newName.trim()">
          {{ creating ? '创建中…' : '＋ 新建空白课表' }}
        </button>
      </form>
    </div>

    <div v-if="currentSchedules.length" class="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      <article
        v-for="schedule in currentSchedules"
        :key="schedule.id"
        class="shelf-card"
        :class="{
          'shelf-card--active': schedule.id === activeId,
          'shelf-card--dragging': drag && drag.active && drag.id === schedule.id,
        }"
        :data-schedule-id="schedule.id"
        data-shelf-card="current"
      >
        <div class="shelf-preview relative" @pointerdown="startDrag($event, schedule)">
          <ScheduleMiniPreview :slots="schedule.slots" :timing="schedule.timing" />
          <span v-if="schedule.id === activeId" class="shelf-badge shelf-badge--active">正在使用</span>
          <span v-else-if="schedule.is_public" class="shelf-badge shelf-badge--public">公开中</span>
          <span v-else class="shelf-badge">仅自己</span>
          <button
            type="button"
            class="shelf-grip"
            :disabled="busy || creating"
            :aria-label="`拖动排序：${schedule.original_name || '未命名课表'}`"
            title="拖动调整顺序，或按方向键移动"
            @pointerdown.stop.prevent="startDrag($event, schedule)"
            @keydown.up.prevent="reorderByKeyboard(schedule, -1)"
            @keydown.down.prevent="reorderByKeyboard(schedule, 1)"
            @keydown.left.prevent="reorderByKeyboard(schedule, -1)"
            @keydown.right.prevent="reorderByKeyboard(schedule, 1)"
          >⠿</button>
        </div>

        <form
          v-if="renamingId === schedule.id"
          class="mt-2.5 space-y-2"
          @submit.prevent="submitRename(schedule)"
        >
          <input
            v-model="renameDraft"
            class="input !py-1.5 text-sm"
            maxlength="255"
            aria-label="课表新名称"
            placeholder="例如：2026 秋 · 大三上"
            @keyup.esc="cancelRename"
          />
          <p v-if="renameError" class="text-[11px] text-red-600">{{ renameError }}</p>
          <div class="flex gap-2">
            <button type="submit" class="btn-xs-success" :disabled="busy">保存名称</button>
            <button type="button" class="btn-xs" @click="cancelRename">取消</button>
          </div>
        </form>

        <template v-else>
          <h4 class="mt-2.5 truncate text-sm font-semibold text-ink" :title="schedule.original_name || '未命名课表'">
            {{ schedule.original_name || '未命名课表' }}
          </h4>
          <p class="mt-1 text-[11px] leading-5 text-faint">
            {{ formatLabel(schedule) }} · {{ schedule.slots.length }} 个时段 · {{ dateLabel(schedule) }}
          </p>
        </template>

        <div class="mt-2.5 flex flex-wrap gap-1.5">
          <button
            v-if="schedule.id !== activeId"
            type="button"
            class="btn-xs"
            :disabled="busy"
            title="切换到这张课表"
            @click="emit('select', schedule)"
          >使用</button>
          <button type="button" class="btn-xs" :disabled="busy || renamingId === schedule.id" @click="startRename(schedule)">命名</button>
          <button type="button" class="btn-xs" :disabled="busy" title="存档到历史课表" @click="emit('archive', schedule)">存档</button>
          <button v-if="publicShareEnabled || schedule.is_public" type="button" class="btn-xs" :disabled="busy" @click="emit('toggleShare', schedule)">
            {{ schedule.is_public ? '仅自己' : '公开' }}
          </button>
          <button type="button" class="btn-xs-danger" :disabled="busy" @click="emit('remove', schedule)">删除</button>
        </div>
      </article>
    </div>

    <div
      v-else
      class="mt-4 rounded-2xl border border-dashed border-primary-200 bg-primary-50/40 px-4 py-6 text-center text-sm text-sub"
    >
      {{ fileImportEnabled ? '课表架还是空的。可以在上方新建空白课表，或从右侧上传文件。' : '课表架还是空的。可以在上方新建空白课表。' }}
    </div>

    <div v-if="archivedSchedules.length" class="mt-5 rounded-2xl border border-primary-100/70 bg-white/40 p-3">
      <button
        type="button"
        class="flex w-full items-center justify-between gap-2 px-1 text-left"
        :aria-expanded="showArchived"
        @click="showArchived = !showArchived"
      >
        <span class="text-sm font-semibold text-ink">历史课表 · 已存档 {{ archivedSchedules.length }}</span>
        <span class="text-xs text-faint">{{ showArchived ? '收起' : '展开' }}</span>
      </button>
      <div v-if="showArchived" class="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        <article
          v-for="schedule in archivedSchedules"
          :key="schedule.id"
          class="shelf-card shelf-card--archived"
          :class="{ 'shelf-card--dragging': drag && drag.active && drag.id === schedule.id }"
          :data-schedule-id="schedule.id"
          data-shelf-card="archived"
        >
          <div class="shelf-preview relative" @pointerdown="startDrag($event, schedule)">
            <ScheduleMiniPreview :slots="schedule.slots" :timing="schedule.timing" />
            <span class="shelf-badge shelf-badge--muted">已存档</span>
            <button
              type="button"
              class="shelf-grip"
              :disabled="busy || creating"
              :aria-label="`拖动排序：${schedule.original_name || '未命名课表'}`"
              title="拖动调整顺序，或按方向键移动"
              @pointerdown.stop.prevent="startDrag($event, schedule)"
              @keydown.up.prevent="reorderByKeyboard(schedule, -1)"
              @keydown.down.prevent="reorderByKeyboard(schedule, 1)"
              @keydown.left.prevent="reorderByKeyboard(schedule, -1)"
              @keydown.right.prevent="reorderByKeyboard(schedule, 1)"
            >⠿</button>
          </div>

          <form
            v-if="renamingId === schedule.id"
            class="mt-2.5 space-y-2"
            @submit.prevent="submitRename(schedule)"
          >
            <input
              v-model="renameDraft"
              class="input !py-1.5 text-sm"
              maxlength="255"
              aria-label="课表新名称"
              @keyup.esc="cancelRename"
            />
            <p v-if="renameError" class="text-[11px] text-red-600">{{ renameError }}</p>
            <div class="flex gap-2">
              <button type="submit" class="btn-xs-success" :disabled="busy">保存名称</button>
              <button type="button" class="btn-xs" @click="cancelRename">取消</button>
            </div>
          </form>

          <template v-else>
            <h4 class="mt-2.5 truncate text-sm font-semibold text-ink" :title="schedule.original_name || '未命名课表'">
              {{ schedule.original_name || '未命名课表' }}
            </h4>
            <p class="mt-1 text-[11px] leading-5 text-faint">
              {{ formatLabel(schedule) }} · {{ schedule.slots.length }} 个时段 · {{ dateLabel(schedule) }}
            </p>
          </template>

          <div class="mt-2.5 flex flex-wrap gap-1.5">
            <button type="button" class="btn-xs-success" :disabled="busy" @click="emit('restore', schedule)">恢复到课表架</button>
            <button type="button" class="btn-xs" :disabled="busy || renamingId === schedule.id" @click="startRename(schedule)">命名</button>
            <button type="button" class="btn-xs-danger" :disabled="busy" @click="emit('remove', schedule)">删除</button>
          </div>
        </article>
      </div>
    </div>
  </section>
</template>

<style scoped>
.shelf-card {
  display: flex;
  min-width: 0;
  flex-direction: column;
  border: 1px solid rgba(255, 255, 255, 0.8);
  border-radius: 1rem;
  padding: 0.7rem;
  background: rgba(255, 255, 255, 0.62);
  box-shadow: 0 8px 20px rgba(31, 27, 51, 0.05);
  transition: border-color 0.16s ease, background 0.16s ease, transform 0.16s ease;
}

.shelf-card:hover {
  border-color: rgba(107, 92, 231, 0.28);
  background: rgba(255, 255, 255, 0.82);
}

.shelf-card--active {
  border-color: rgba(107, 92, 231, 0.45);
  box-shadow: 0 0 0 2px rgba(107, 92, 231, 0.12), 0 8px 20px rgba(31, 27, 51, 0.06);
}

.shelf-card--archived {
  opacity: 0.78;
  background: rgba(250, 250, 253, 0.55);
}

.shelf-preview {
  cursor: grab;
}

.shelf-grip {
  position: absolute;
  top: 0.28rem;
  right: 0.28rem;
  display: inline-flex;
  height: 1.5rem;
  width: 1.5rem;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(107, 92, 231, 0.18);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  color: #6e698c;
  font-size: 0.8rem;
  line-height: 1;
  cursor: grab;
  touch-action: none;
}

.shelf-grip:hover {
  border-color: rgba(107, 92, 231, 0.45);
  color: #493db0;
}

.shelf-grip:active {
  cursor: grabbing;
}

.shelf-grip:focus-visible {
  outline: 2px solid #493db0;
  outline-offset: 2px;
}

.shelf-grip:disabled {
  cursor: not-allowed;
  opacity: 0.4;
}

.shelf-card--dragging {
  border-color: rgba(107, 92, 231, 0.5);
  opacity: 0.55;
  transform: scale(0.985);
}

:global(body.shelf-dragging) {
  cursor: grabbing;
}

:global(body.shelf-dragging *) {
  cursor: grabbing !important;
  user-select: none;
}

.shelf-badge {
  position: absolute;
  top: 0.35rem;
  left: 0.35rem;
  border-radius: 999px;
  padding: 0.12rem 0.4rem;
  background: rgba(255, 255, 255, 0.9);
  color: #6e698c;
  font-size: 0.56rem;
  font-weight: 700;
  line-height: 1.4;
}

.shelf-badge--active { background: #6b5ce7; color: white; }
.shelf-badge--public { background: #ecfdf5; color: #047857; }
.shelf-badge--muted { background: #f1f0f8; color: #8d88a8; }
</style>
