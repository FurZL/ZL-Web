<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import UserAvatar from '@/components/UserAvatar.vue'
import {
  compareSchedules,
  completeScheduleUpload,
  createScheduleUploadIntent,
  deleteSchedule,
  getMySchedules,
  getSharedSchedule,
  setScheduleVisibility,
} from '@/api/schedule'
import type {
  ScheduleCompareResult,
  ScheduleRecord,
  ScheduleSlot,
} from '@/types'

const step = ref(1)

// ---------- 我的课表 ----------
const mySchedules = ref<ScheduleRecord[]>([])
const activeSchedule = ref<ScheduleRecord | null>(null)
const loadingMine = ref(true)
const mineError = ref('')

async function loadMine() {
  loadingMine.value = true
  mineError.value = ''
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
    mineError.value = e instanceof Error ? e.message : '课表加载失败'
  } finally {
    loadingMine.value = false
  }
}

onMounted(loadMine)

const mySlots = computed<ScheduleSlot[]>(() => activeSchedule.value?.slots ?? [])

// ---------- 上传 ----------
const fileInput = ref<HTMLInputElement | null>(null)
const uploadError = ref('')
const uploading = ref(false)
const uploadDone = ref(false)

function pickFile() {
  fileInput.value?.click()
}

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  const f = input.files?.[0]
  if (f) void uploadFile(f)
  input.value = ''
}

function onDrop(e: DragEvent) {
  const f = e.dataTransfer?.files?.[0]
  if (f) void uploadFile(f)
}

async function uploadFile(f: File) {
  const name = f.name.toLowerCase()
  if (!name.endsWith('.ics') && !name.endsWith('.txt')) {
    uploadError.value = '仅支持 .ics / .txt 文件（PDF 暂未支持）'
    return
  }
  uploading.value = true
  uploadError.value = ''
  uploadDone.value = false
  try {
    const intent = await createScheduleUploadIntent(f.name, f.size)
    const put = await fetch(intent.upload_url, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/octet-stream' },
      body: f,
    })
    if (!put.ok) {
      throw new Error('文件上传到存储失败，请重试')
    }
    const record = await completeScheduleUpload(intent, f.name)
    mySchedules.value = [record, ...mySchedules.value]
    activeSchedule.value = record
    uploadDone.value = true
  } catch (e) {
    uploadError.value = e instanceof Error ? e.message : '上传失败'
  } finally {
    uploading.value = false
  }
}

// 分享开关 / 删除
const togglingId = ref<string | null>(null)
async function toggleShare(s: ScheduleRecord) {
  togglingId.value = s.id
  try {
    const updated = await setScheduleVisibility(s.id, !s.is_public)
    const idx = mySchedules.value.findIndex((x) => x.id === s.id)
    if (idx >= 0) mySchedules.value[idx] = updated
    if (activeSchedule.value?.id === s.id) activeSchedule.value = updated
  } catch (e) {
    alert(e instanceof Error ? e.message : '操作失败')
  } finally {
    togglingId.value = null
  }
}

async function removeSchedule(s: ScheduleRecord) {
  if (!confirm(`确定删除课表「${s.original_name ?? '未命名'}」吗？`)) return
  try {
    await deleteSchedule(s.id)
    mySchedules.value = mySchedules.value.filter((x) => x.id !== s.id)
    if (activeSchedule.value?.id === s.id) {
      activeSchedule.value = mySchedules.value[0] ?? null
    }
  } catch (e) {
    alert(e instanceof Error ? e.message : '删除失败')
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

// ---------- 网格渲染 ----------
const days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
const maxLesson = 12

type CellKind = 'both-busy' | 'one-busy' | 'both-free' | 'same-room'

function slotCovers(s: ScheduleSlot, weekday: number, lesson: number) {
  return s.weekday === weekday && lesson >= s.lesson_start && lesson <= s.lesson_end
}

function cellKind(day: number, lesson: number): CellKind {
  const mine = mySlots.value.some((s) => slotCovers(s, day, lesson))
  const theirs = partnerSlots.value.some((s) => slotCovers(s, day, lesson))
  if (mine && theirs) {
    const sameRoom = result.value?.same_classroom.some(
      (c) => c.weekday === day && slotCovers(c.a, day, lesson),
    )
    return sameRoom ? 'same-room' : 'both-busy'
  }
  if (mine || theirs) return 'one-busy'
  return 'both-free'
}

const grid = computed(() => {
  const rows: { day: number; lessons: CellKind[] }[] = []
  for (let d = 0; d < 7; d++) {
    const lessons: CellKind[] = []
    for (let l = 1; l <= maxLesson; l++) lessons.push(cellKind(d, l))
    rows.push({ day: d, lessons })
  }
  return rows
})

const freeSlots = computed(() => {
  if (result.value) {
    return result.value.both_free.map((f) => ({
      day: days[f.weekday],
      slots: f.lesson_start === f.lesson_end
        ? `第 ${f.lesson_start} 节`
        : `第 ${f.lesson_start}-${f.lesson_end} 节`,
    }))
  }
  const out: { day: string; slots: string }[] = []
  for (let d = 0; d < 7; d++) {
    const free = grid.value[d].lessons
      .map((k, i) => (k === 'both-free' ? i + 1 : null))
      .filter((n): n is number => n !== null)
    if (free.length) out.push({ day: days[d], slots: `第 ${free.join('、')} 节` })
  }
  return out
})

const sameRoomList = computed(() =>
  (result.value?.same_classroom ?? []).map((c) => ({
    day: days[c.weekday],
    name: c.a.name,
    location: c.a.location,
    range: `${c.a.lesson_start}-${c.a.lesson_end} 节`,
  })),
)

const overlapList = computed(() =>
  (result.value?.overlaps ?? []).map((c) => ({
    day: days[c.weekday],
    mine: c.a.name,
    theirs: c.b.name,
    range: `${Math.max(c.a.lesson_start, c.b.lesson_start)}-${Math.min(c.a.lesson_end, c.b.lesson_end)} 节`,
  })),
)

const cellStyle: Record<CellKind, string> = {
  'both-busy': 'bg-blush/30 text-blush',
  'one-busy': 'bg-primary-100 text-primary-400',
  'both-free': 'bg-emerald-100 text-emerald-600',
  'same-room': 'bg-amber-100 text-amber-600',
}

function fmtDate(iso: string | null) {
  if (!iso) return ''
  return iso.slice(0, 10)
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

    <!-- Step 1：我的课表 -->
    <div v-if="step === 1" class="mt-8 glass-card p-8 max-w-2xl">
      <!-- 已有课表 -->
      <template v-if="mySchedules.length > 0">
        <h2 class="text-sm font-medium text-sub mb-3">我的课表</h2>
        <div class="space-y-2">
          <div
            v-for="s in mySchedules"
            :key="s.id"
            class="flex items-center gap-3 rounded-xl px-4 py-3 transition cursor-pointer border"
            :class="activeSchedule?.id === s.id ? 'bg-primary-50 border-primary-300 ring-1 ring-primary-200' : 'bg-white/60 border-white/60 hover:border-primary-200'"
            @click="activeSchedule = s"
          >
            <div class="flex-1 min-w-0">
              <p class="text-sm text-ink font-medium truncate">{{ s.original_name || '未命名课表' }}</p>
              <p class="text-xs text-faint mt-0.5">
                {{ s.format?.toUpperCase() }} · {{ s.slots.length }} 门课 · {{ fmtDate(s.created_at) }}
              </p>
            </div>
            <button
              class="text-xs px-2.5 py-1 rounded-full border transition"
              :class="s.is_public ? 'bg-emerald-100 text-emerald-700 border-emerald-300' : 'bg-white text-faint border-gray-200'"
              :disabled="togglingId === s.id"
              @click.stop="toggleShare(s)"
            >
              {{ s.is_public ? '公开中' : '私有' }}
            </button>
            <button class="text-xs text-faint hover:text-red-500 transition" @click.stop="removeSchedule(s)">
              删除
            </button>
          </div>
        </div>

        <div v-if="activeSchedule" class="mt-6">
          <h3 class="text-sm font-medium text-sub mb-3">课程预览（{{ activeSchedule.slots.length }} 门）</h3>
          <div class="space-y-2 max-h-56 overflow-auto">
            <div v-for="(c, i) in activeSchedule.slots" :key="i" class="flex items-center gap-3 text-sm bg-white/60 rounded-lg px-3 py-2">
              <span class="text-faint text-xs w-8">{{ days[c.weekday] }}</span>
              <span class="text-ink flex-1">{{ c.name }}</span>
              <span class="text-faint text-xs">{{ c.location }} · {{ c.lesson_start }}-{{ c.lesson_end }} 节</span>
            </div>
          </div>
        </div>

        <div class="mt-4 bg-primary-50 rounded-xl p-4 text-sm text-primary-800">
          <p>
            想让圈友能对比你的课表？把课表设为
            <span class="font-medium">「公开中」</span>
            即可。公开后，对方在下一步输入你的用户名就能拉到课表。
          </p>
        </div>

        <div class="mt-6 flex gap-3">
          <button class="btn-ghost" @click="uploadDone = false">换一份课表</button>
          <button class="btn-primary flex-1" :disabled="!activeSchedule" @click="step = 2">
            下一步：选择对比对象
          </button>
        </div>
      </template>

      <!-- 空状态：上传 -->
      <div
        class="border-2 border-dashed rounded-xl2 p-14 text-center transition cursor-pointer"
        :class="uploadError ? 'border-red-300 bg-red-50/50' : uploadDone ? 'border-emerald-300 bg-emerald-50/50' : 'border-primary-200 hover:border-primary-400'"
        @click="pickFile"
        @dragover.prevent
        @drop.prevent="onDrop"
      >
        <input
          ref="fileInput"
          type="file"
          accept=".ics,.txt"
          class="hidden"
          @change="onFileChange"
        />
        <div v-if="uploading" class="flex flex-col items-center">
          <div class="w-10 h-10 border-4 border-primary-200 border-t-primary rounded-full animate-spin"></div>
          <p class="mt-4 text-sm text-sub">正在上传并解析课表…</p>
        </div>
        <div v-else-if="uploadError" class="flex flex-col items-center">
          <div class="w-14 h-14 rounded-full bg-red-100 flex items-center justify-center text-2xl">!</div>
          <p class="mt-3 text-red-600 font-medium">{{ uploadError }}</p>
          <p class="mt-1 text-xs text-faint">点击重新选择文件</p>
        </div>
        <div v-else class="flex flex-col items-center">
          <div class="w-14 h-14 rounded-full bg-primary-50 flex items-center justify-center text-3xl text-primary">📅</div>
          <p class="mt-4 text-ink">拖拽课表文件到这里，或点击选择</p>
          <p class="mt-1 text-sm text-faint">支持 .ics / .txt 文件（PDF 暂未支持）</p>
        </div>
      </div>

      <div v-if="uploadError" class="mt-4">
        <button class="btn-ghost w-full" @click="uploadError = ''">返回</button>
      </div>
    </div>

    <!-- Step 2：选择对比对象 -->
    <div v-else-if="step === 2" class="mt-8 glass-card p-8 max-w-2xl">
      <label class="label">输入圈友的用户名</label>
      <div class="flex gap-2">
        <input
          v-model="partnerName"
          class="input flex-1"
          placeholder="例如：fluffy_zjut"
          @keyup.enter="searchPartner"
        />
        <button class="btn-primary !px-5" :disabled="partnerSearching" @click="searchPartner">
          {{ partnerSearching ? '查找中…' : '查找' }}
        </button>
      </div>
      <p class="mt-2 text-xs text-faint">对方需将自己的课表设为「公开中」才能被对比。</p>

      <div v-if="partnerError" class="mt-4 text-sm text-red-600">{{ partnerError }}</div>

      <div v-if="partner" class="mt-4">
        <div class="flex items-center gap-3 p-4 rounded-xl bg-primary-50 ring-2 ring-primary-300">
          <UserAvatar :name="partner.owner?.display_name ?? partnerName" :size="40" />
          <div class="flex-1">
            <p class="text-sm text-ink font-medium">{{ partner.owner?.display_name ?? partnerName }}</p>
            <p class="text-xs text-faint">
              @{{ partner.owner?.username ?? partnerName }} · {{ partner.slots.length }} 门课
            </p>
          </div>
          <span class="text-primary font-medium text-sm">已选 ✓</span>
        </div>

        <div class="mt-4">
          <h3 class="text-sm font-medium text-sub mb-2">TA 的课程预览</h3>
          <div class="space-y-1.5 max-h-48 overflow-auto">
            <div v-for="(c, i) in partner.slots" :key="i" class="flex items-center gap-3 text-sm bg-white/60 rounded-lg px-3 py-1.5">
              <span class="text-faint text-xs w-8">{{ days[c.weekday] }}</span>
              <span class="text-ink flex-1">{{ c.name }}</span>
              <span class="text-faint text-xs">{{ c.location }} · {{ c.lesson_start }}-{{ c.lesson_end }} 节</span>
            </div>
          </div>
        </div>
      </div>

      <div v-if="compareError" class="mt-4 text-sm text-red-600">{{ compareError }}</div>

      <div class="mt-6 flex gap-3">
        <button class="btn-ghost flex-1" @click="step = 1">上一步</button>
        <button
          class="btn-primary flex-1"
          :disabled="!partner || comparing"
          :class="{ 'opacity-50 cursor-not-allowed': !partner || comparing }"
          @click="runCompare"
        >
          {{ comparing ? '对比中…' : '开始对比' }}
        </button>
      </div>
    </div>

    <!-- Step 3：对比结果 -->
    <div v-else class="mt-8">
      <div class="glass-card p-8">
        <div class="flex flex-wrap items-center gap-4">
          <div class="flex items-center gap-2">
            <UserAvatar :name="'我'" :size="32" />
            <span class="text-sm text-ink font-medium">我</span>
          </div>
          <span class="text-faint">vs</span>
          <div class="flex items-center gap-2">
            <UserAvatar :name="partner?.owner?.display_name ?? ''" :size="32" />
            <span class="text-sm text-ink font-medium">{{ partner?.owner?.display_name }}</span>
          </div>
          <div class="ml-auto flex gap-2">
            <button class="btn-ghost !px-4 !py-1.5 text-xs" @click="step = 2">重新选择</button>
          </div>
        </div>

        <!-- 图例 -->
        <div class="mt-6 flex flex-wrap gap-4 text-xs text-sub">
          <span class="flex items-center gap-1.5"><span class="w-3.5 h-3.5 rounded bg-emerald-100 border border-emerald-300"></span>双方都空闲（适合约）</span>
          <span class="flex items-center gap-1.5"><span class="w-3.5 h-3.5 rounded bg-primary-100 border border-primary-300"></span>有一方有课</span>
          <span class="flex items-center gap-1.5"><span class="w-3.5 h-3.5 rounded bg-amber-100 border border-amber-300"></span>同教室同时间（意外相遇！）</span>
          <span class="flex items-center gap-1.5"><span class="w-3.5 h-3.5 rounded bg-blush/20 border border-blush/40"></span>双方都有课</span>
        </div>

        <!-- 周课表网格 -->
        <div class="mt-6 overflow-x-auto">
          <div class="min-w-[640px]">
            <div class="grid grid-cols-[48px_repeat(7,1fr)] gap-1">
              <div></div>
              <div v-for="d in days" :key="d" class="text-center text-xs font-medium text-sub py-2">{{ d }}</div>
            </div>
            <div v-for="lesson in maxLesson" :key="lesson" class="grid grid-cols-[48px_repeat(7,1fr)] gap-1 mt-1">
              <div class="text-right pr-2 text-[10px] text-faint leading-7">{{ lesson }}</div>
              <div
                v-for="d in 7"
                :key="d"
                class="h-7 rounded-md text-[10px] flex items-center justify-center font-medium transition"
                :class="cellStyle[grid[d - 1].lessons[lesson - 1]]"
              >
                {{ grid[d - 1].lessons[lesson - 1] === 'both-free' ? '·' : '' }}
              </div>
            </div>
          </div>
        </div>

        <!-- 推荐空闲时段 -->
        <div class="mt-8">
          <h3 class="text-sm font-semibold text-ink mb-3">推荐空闲时段</h3>
          <div v-if="freeSlots.length" class="space-y-2">
            <div v-for="f in freeSlots" :key="f.day" class="flex items-center gap-3 text-sm bg-emerald-50 rounded-lg px-4 py-2.5">
              <span class="text-emerald-700 font-medium w-12">{{ f.day }}</span>
              <span class="text-emerald-700">{{ f.slots }}</span>
            </div>
          </div>
          <p v-else class="text-sm text-faint">本学期你们似乎没有共同空闲时段，换个学期再约吧～</p>
          <p class="mt-4 text-xs text-faint">以上时段双方都无课（按整学期安全空闲计算），快约起来吧～</p>
        </div>

        <!-- 同教室 -->
        <div v-if="sameRoomList.length" class="mt-8">
          <h3 class="text-sm font-semibold text-ink mb-3">同教室时段（意外相遇！）</h3>
          <div class="space-y-2">
            <div v-for="(r, i) in sameRoomList" :key="i" class="flex items-center gap-3 text-sm bg-amber-50 rounded-lg px-4 py-2.5">
              <span class="text-amber-700 font-medium w-12">{{ r.day }}</span>
              <span class="text-amber-700 flex-1">{{ r.name }} · {{ r.location }}</span>
              <span class="text-amber-600 text-xs">{{ r.range }}</span>
            </div>
          </div>
        </div>

        <!-- 冲突 -->
        <div v-if="overlapList.length" class="mt-8">
          <h3 class="text-sm font-semibold text-ink mb-3">时间冲突</h3>
          <div class="space-y-2">
            <div v-for="(r, i) in overlapList" :key="i" class="flex items-center gap-3 text-sm bg-red-50 rounded-lg px-4 py-2.5">
              <span class="text-red-700 font-medium w-12">{{ r.day }}</span>
              <span class="text-red-700 flex-1">{{ r.mine }} vs {{ r.theirs }}</span>
              <span class="text-red-600 text-xs">{{ r.range }}</span>
            </div>
          </div>
          <p class="mt-3 text-xs text-faint">冲突已按周次交集计算，只有真正同时上课才算。</p>
        </div>
      </div>
    </div>
  </div>
</template>
