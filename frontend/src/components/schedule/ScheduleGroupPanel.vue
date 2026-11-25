<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import ScheduleWeekPicker from '@/components/schedule/ScheduleWeekPicker.vue'
import { useDialog } from '@/composables/useDialog'
import {
  approveScheduleGroupMember,
  createScheduleGroup,
  deleteScheduleGroup,
  getScheduleGroup,
  getScheduleGroups,
  joinScheduleGroup,
  rejectScheduleGroupMember,
  removeScheduleGroupMember,
  setScheduleGroupSchedule,
  updateScheduleGroup,
} from '@/api/schedule'
import type {
  ScheduleGroupDetail,
  ScheduleGroupJoinMode,
  ScheduleGroupMember,
  ScheduleGroupSummary,
  ScheduleRecord,
} from '@/types'
import { scheduleWeeks } from './calendar'

const props = withDefaults(defineProps<{
  schedules: ScheduleRecord[]
  initialGroupId?: string | null
  comparing?: boolean
}>(), {
  initialGroupId: null,
  comparing: false,
})

const emit = defineEmits<{
  compare: [payload: {
    groupId: string
    groupName: string
    member: ScheduleGroupMember
    week: number | null
    myScheduleId: string
  }]
}>()

const { showToast, showConfirm } = useDialog()
const groups = ref<ScheduleGroupSummary[]>([])
const detail = ref<ScheduleGroupDetail | null>(null)
const selectedId = ref<string | null>(null)
const loadingGroups = ref(true)
const loadingDetail = ref(false)
const busy = ref(false)
const error = ref('')
const selectedWeek = ref<number | null>(null)
const createName = ref('我的课搭子群')
const createMode = ref<ScheduleGroupJoinMode>('open')
const joinCode = ref('')

const activeSchedules = computed(() => props.schedules.filter((item) => !item.is_archived))
const weeks = computed(() => scheduleWeeks(
  detail.value
    ? detail.value.members.flatMap((member) => member.slots)
    : props.schedules.flatMap((schedule) => schedule.slots),
))
const pendingViewer = computed(() => detail.value?.my.status === 'pending')

function displayName(member: ScheduleGroupMember) {
  return member.is_me ? `${member.display_name}（你）` : member.display_name
}

async function loadGroups() {
  loadingGroups.value = true
  try {
    const data = await getScheduleGroups()
    groups.value = data.items
  } catch (e) {
    error.value = e instanceof Error ? e.message : '群组加载失败'
  } finally {
    loadingGroups.value = false
  }
}

async function loadDetail() {
  const id = selectedId.value
  if (!id) return
  loadingDetail.value = true
  error.value = ''
  try {
    detail.value = await getScheduleGroup(id, selectedWeek.value)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '群组详情加载失败'
    if (!detail.value) selectedId.value = null
  } finally {
    loadingDetail.value = false
  }
}

async function selectGroup(id: string) {
  selectedId.value = id
  selectedWeek.value = null
  detail.value = null
  await loadDetail()
}

async function createGroup() {
  const name = createName.value.trim()
  if (!name || busy.value) return
  busy.value = true
  error.value = ''
  try {
    const created = await createScheduleGroup(name, createMode.value)
    showToast('群组已创建，把邀请码发给同学')
    await loadGroups()
    await selectGroup(created.id)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '创建群组失败'
  } finally {
    busy.value = false
  }
}

async function joinGroup() {
  const code = joinCode.value.trim()
  if (!code || busy.value) return
  busy.value = true
  error.value = ''
  try {
    const joined = await joinScheduleGroup(code)
    showToast(joined.my.status === 'active' ? '已加入群组' : '入群申请已发送，等待群主同意')
    joinCode.value = ''
    await loadGroups()
    await selectGroup(joined.id)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加入群组失败'
  } finally {
    busy.value = false
  }
}

function backToList() {
  detail.value = null
  selectedId.value = null
  selectedWeek.value = null
  error.value = ''
  void loadGroups()
}

async function copyCode() {
  if (!detail.value?.code) return
  try {
    await navigator.clipboard.writeText(detail.value.code)
    showToast('邀请码已复制')
  } catch {
    showToast('复制失败，请手动选择邀请码')
  }
}

async function setMySchedule(event: Event) {
  const value = (event.target as HTMLSelectElement).value
  if (!detail.value || busy.value) return
  busy.value = true
  error.value = ''
  try {
    await setScheduleGroupSchedule(detail.value.id, value || null)
    await loadDetail()
    showToast(value ? '已把课表共享给群组' : '已取消共享课表')
  } catch (e) {
    error.value = e instanceof Error ? e.message : '共享课表失败'
  } finally {
    busy.value = false
  }
}

async function approve(memberUserId: string) {
  if (!detail.value || busy.value) return
  busy.value = true
  try {
    await approveScheduleGroupMember(detail.value.id, memberUserId)
    await loadDetail()
    showToast('已同意入群')
  } catch (e) {
    error.value = e instanceof Error ? e.message : '审批失败'
  } finally {
    busy.value = false
  }
}

async function reject(memberUserId: string) {
  if (!detail.value || busy.value) return
  busy.value = true
  try {
    await rejectScheduleGroupMember(detail.value.id, memberUserId)
    await loadDetail()
    showToast('已拒绝入群申请')
  } catch (e) {
    error.value = e instanceof Error ? e.message : '审批失败'
  } finally {
    busy.value = false
  }
}

async function removeMember(member: ScheduleGroupMember) {
  if (!detail.value || busy.value) return
  const isSelf = member.is_me
  const message = isSelf ? '确定退出这个群组吗？' : `确定把「${member.display_name}」移出群组吗？`
  if (!(await showConfirm(message))) return
  busy.value = true
  try {
    await removeScheduleGroupMember(detail.value.id, member.user_id)
    if (isSelf) {
      detail.value = null
      selectedId.value = null
      await loadGroups()
      showToast('已退出群组')
    } else {
      await loadDetail()
      showToast('已移出成员')
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : '操作失败'
  } finally {
    busy.value = false
  }
}

function leaveGroup() {
  const me = detail.value?.members.find((member) => member.is_me)
  if (me) void removeMember(me)
}

async function deleteGroup() {
  if (!detail.value || busy.value) return
  if (!(await showConfirm('解散群组后邀请码失效，成员共享关系也会移除。确定继续吗？'))) return
  busy.value = true
  try {
    await deleteScheduleGroup(detail.value.id)
    detail.value = null
    selectedId.value = null
    await loadGroups()
    showToast('群组已解散')
  } catch (e) {
    error.value = e instanceof Error ? e.message : '解散失败'
  } finally {
    busy.value = false
  }
}

async function changeJoinMode(event: Event) {
  if (!detail.value || busy.value) return
  const mode = (event.target as HTMLSelectElement).value as ScheduleGroupJoinMode
  busy.value = true
  try {
    await updateScheduleGroup(detail.value.id, { join_mode: mode })
    await loadDetail()
    showToast(mode === 'open' ? '现在拿到邀请码即可入群' : '现在入群需要群主同意')
  } catch (e) {
    error.value = e instanceof Error ? e.message : '修改失败'
  } finally {
    busy.value = false
  }
}

function compareMember(member: ScheduleGroupMember) {
  if (!detail.value || !member.stats || !detail.value.my.schedule_id) return
  emit('compare', {
    groupId: detail.value.id,
    groupName: detail.value.name,
    member,
    week: selectedWeek.value,
    myScheduleId: detail.value.my.schedule_id,
  })
}

watch(selectedWeek, () => {
  if (detail.value && !loadingDetail.value) void loadDetail()
})

watch(() => props.initialGroupId, (id) => {
  if (id && detail.value?.id !== id) void selectGroup(id)
})

onMounted(async () => {
  await loadGroups()
  if (props.initialGroupId) await selectGroup(props.initialGroupId)
})
</script>

<template>
  <section class="glass-card mt-5 p-5 sm:p-7">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <p class="text-xs font-semibold uppercase tracking-[0.18em] text-primary-500">Study group</p>
        <h2 class="mt-1 text-xl font-bold text-ink">群组对比</h2>
        <p class="mt-1 text-sm text-sub">
          加入私密群组，成员各选一份课表共享；这里只显示每个人和你的忙闲对比，不会公开课表。
        </p>
      </div>
      <button v-if="detail" type="button" class="btn-sm" :disabled="busy || loadingDetail" @click="backToList">← 群组列表</button>
    </div>

    <p v-if="error" role="alert" class="mt-3 rounded-xl bg-red-50 p-3 text-sm text-red-700">{{ error }}</p>

    <!-- 未选择群组：创建 / 加入 / 我的群组 -->
    <template v-if="!detail">
      <div class="mt-5 grid gap-4 lg:grid-cols-2">
        <form class="rounded-2xl border border-primary-100 bg-white/50 p-4" @submit.prevent="createGroup">
          <h3 class="text-sm font-bold text-ink">创建群组</h3>
          <label class="label mt-3">群组名称
            <input v-model="createName" class="input mt-1" maxlength="50" required :disabled="busy" />
          </label>
          <label class="label mt-3">谁能进群
            <select v-model="createMode" class="input mt-1" :disabled="busy">
              <option value="open">拿到邀请码就能进</option>
              <option value="approval">需要群主同意</option>
            </select>
          </label>
          <button type="submit" class="btn-primary mt-4 w-full" :disabled="busy || !createName.trim()">
            {{ busy ? '创建中…' : '创建群组' }}
          </button>
        </form>

        <form class="rounded-2xl border border-primary-100 bg-white/50 p-4" @submit.prevent="joinGroup">
          <h3 class="text-sm font-bold text-ink">用邀请码加入</h3>
          <label class="label mt-3">邀请码
            <input v-model="joinCode" class="input mt-1 font-mono uppercase tracking-wider" maxlength="12" placeholder="例如 A7K9P2QX" required :disabled="busy" />
          </label>
          <button type="submit" class="btn-primary mt-4 w-full" :disabled="busy || !joinCode.trim()">
            {{ busy ? '加入中…' : '加入群组' }}
          </button>
        </form>
      </div>

      <div class="mt-5">
        <h3 class="text-sm font-bold text-ink">我的群组</h3>
        <div v-if="loadingGroups" class="mt-3 h-16 animate-pulse rounded-xl bg-primary-50"></div>
        <div v-else-if="!groups.length" class="mt-3 rounded-xl border border-dashed border-primary-200 px-4 py-5 text-sm text-sub">
          还没有加入群组。创建一个，把邀请码发给同学即可。
        </div>
        <div v-else class="mt-3 grid gap-2">
          <button
            v-for="group in groups"
            :key="group.id"
            type="button"
            class="flex items-center justify-between gap-3 rounded-xl border border-white/70 bg-white/60 px-4 py-3 text-left transition hover:border-primary-200 hover:bg-white"
            @click="selectGroup(group.id)"
          >
            <span class="min-w-0">
              <span class="block truncate text-sm font-semibold text-ink">{{ group.name }}</span>
              <span class="mt-0.5 block text-[11px] text-faint">
                {{ group.member_count }} 人
                <template v-if="group.my.status === 'pending'"> · 等待群主同意</template>
                <template v-else-if="group.my.role === 'owner'"> · 你是群主</template>
                <template v-if="group.pending_count"> · {{ group.pending_count }} 人待审批</template>
              </span>
            </span>
            <span class="text-faint">›</span>
          </button>
        </div>
      </div>
    </template>

    <!-- 已选择群组 -->
    <template v-else>
      <div class="mt-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 class="text-lg font-bold text-ink">{{ detail.name }}</h3>
          <p class="mt-1 text-xs text-sub">
            {{ detail.member_count }} 人 · {{ detail.join_mode === 'open' ? '邀请码直接加入' : '需要群主同意' }}
            <template v-if="detail.my.role === 'owner'"> · 你是群主</template>
          </p>
        </div>
        <div v-if="detail.code && detail.my.status === 'active'" class="flex items-center gap-2 rounded-xl bg-primary-50 px-3 py-2">
          <span class="text-[11px] font-semibold text-primary-700">邀请码</span>
          <code class="font-mono text-sm font-bold tracking-wider text-primary-800">{{ detail.code }}</code>
          <button type="button" class="btn-xs" @click="copyCode">复制</button>
        </div>
      </div>

      <div v-if="pendingViewer" class="mt-4 rounded-xl bg-amber-50 p-3 text-sm text-amber-800">
        你的入群申请还在等待群主同意；同意后即可共享课表并查看对比。
      </div>

      <template v-else>
        <div class="mt-4 grid gap-3 lg:grid-cols-2">
          <label class="label">我共享给群的课表
            <select class="input mt-1" :value="detail.my.schedule_id ?? ''" :disabled="busy" @change="setMySchedule">
              <option value="">暂不共享</option>
              <option v-for="schedule in activeSchedules" :key="schedule.id" :value="schedule.id">
                {{ schedule.original_name || '未命名课表' }}
              </option>
            </select>
          </label>
          <div>
            <p class="label">查看哪一周</p>
            <ScheduleWeekPicker v-model="selectedWeek" :weeks="weeks" />
          </div>
        </div>
        <p class="mt-1 text-xs text-sub">只有群成员能看到你选的这份课表；个人日程只显示占用时间。</p>

        <div v-if="detail.pending.length" class="mt-5 rounded-xl border border-amber-200 bg-amber-50/60 p-3">
          <p class="text-sm font-semibold text-amber-900">想进群的人（{{ detail.pending.length }}）</p>
          <div v-for="request in detail.pending" :key="request.user_id" class="mt-2 flex items-center justify-between gap-2 text-sm">
            <span>{{ request.display_name }} <span class="text-xs text-amber-700">@{{ request.username }}</span></span>
            <span class="flex gap-2">
              <button type="button" class="btn-xs-success" :disabled="busy" @click="approve(request.user_id)">同意</button>
              <button type="button" class="btn-xs" :disabled="busy" @click="reject(request.user_id)">拒绝</button>
            </span>
          </div>
        </div>

        <div class="mt-5 space-y-2">
          <article
            v-for="member in detail.members"
            :key="member.user_id"
            class="rounded-xl border border-white/70 bg-white/55 p-3.5"
            :class="{ 'border-primary-200 bg-primary-50/40': member.is_me }"
          >
            <div class="flex flex-wrap items-start justify-between gap-2">
              <div class="min-w-0">
                <p class="truncate text-sm font-semibold text-ink">
                  {{ displayName(member) }}
                  <span v-if="member.role === 'owner'" class="ml-1 rounded-full bg-primary-100 px-1.5 py-0.5 text-[10px] text-primary-700">群主</span>
                  <span v-if="!member.schedule_id" class="ml-1 rounded-full bg-gray-100 px-1.5 py-0.5 text-[10px] text-faint">未共享课表</span>
                </p>
                <p class="mt-1 text-[11px] text-faint">
                  @{{ member.username }} · {{ member.course_count }} 个时段
                  <template v-if="member.schedule_name"> · {{ member.schedule_name }}</template>
                </p>
              </div>
              <div class="flex shrink-0 gap-2">
                <button
                  v-if="!member.is_me && member.stats"
                  type="button"
                  class="btn-xs-success"
                  :disabled="comparing"
                  @click="compareMember(member)"
                >查看对比</button>
                <button
                  v-if="!member.is_me && detail.my.can_manage"
                  type="button"
                  class="btn-xs-danger"
                  :disabled="busy"
                  @click="removeMember(member)"
                >移出</button>
                <button
                  v-if="member.is_me && detail.my.role !== 'owner'"
                  type="button"
                  class="btn-xs-danger"
                  :disabled="busy"
                  @click="removeMember(member)"
                >退群</button>
              </div>
            </div>

            <div v-if="member.stats" class="mt-2 flex flex-wrap gap-1.5 text-[11px]">
              <span class="rounded-full bg-emerald-50 px-2 py-0.5 text-emerald-700">共同空闲 {{ member.stats.both_free }} 节</span>
              <span class="rounded-full bg-rose-50 px-2 py-0.5 text-rose-700">共同忙碌 {{ member.stats.both_busy }} 节</span>
              <span class="rounded-full bg-sky-50 px-2 py-0.5 text-sky-700">你忙 TA 空 {{ member.stats.my_busy_only }} 节</span>
              <span class="rounded-full bg-violet-50 px-2 py-0.5 text-violet-700">TA 忙你空 {{ member.stats.their_busy_only }} 节</span>
              <span class="rounded-full bg-amber-50 px-2 py-0.5 text-amber-700">同教室 {{ member.stats.same_classroom }} 节</span>
            </div>
            <p v-else-if="!member.is_me" class="mt-2 text-[11px] text-faint">
              {{ detail.my.schedule_id ? 'TA 还没共享课表，暂时无法对比。' : '你先在上方共享一份课表，才能看到对比。' }}
            </p>
          </article>
        </div>

        <div class="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-primary-100/70 pt-4">
          <div v-if="detail.my.can_manage" class="flex items-center gap-2 text-xs text-sub">
            <span>进群方式</span>
            <select class="input !w-auto !py-1.5 text-xs" :value="detail.join_mode" :disabled="busy" @change="changeJoinMode">
              <option value="open">邀请码直接加入</option>
              <option value="approval">需要群主同意</option>
            </select>
          </div>
          <div class="flex gap-2">
            <button v-if="detail.my.can_manage" type="button" class="btn-sm-danger" :disabled="busy" @click="deleteGroup">解散群组</button>
            <button v-else type="button" class="btn-sm-danger" :disabled="busy" @click="leaveGroup">退出群组</button>
          </div>
        </div>
      </template>
    </template>
  </section>
</template>
