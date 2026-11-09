<script setup lang="ts">
import { computed, ref } from 'vue'
import UserAvatar from '@/components/UserAvatar.vue'
import { members, mySchedule, theirSchedule } from '@/api/mock'

const step = ref(1)

// Step 1: 上传课表
const uploaded = ref(false)
const fileParsing = ref(false)
function handleDrop() {
  uploaded.value = true
  fileParsing.value = true
  setTimeout(() => {
    fileParsing.value = false
  }, 900)
}

// Step 2: 选择对比对象
const chosenName = ref('')
const chosen = computed(() =>
  members.find((m) => m.displayName === chosenName.value || m.username === chosenName.value),
)

// Step 3: 对比结果
const days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
const maxLesson = 12

type CellKind = 'both-busy' | 'one-busy' | 'both-free' | 'same-room'

function cellKind(day: number, lesson: number): CellKind {
  const mine = mySchedule.some((s) => s.weekday === day && lesson >= s.lessonStart && lesson <= s.lessonEnd)
  const theirs = theirSchedule.some((s) => s.weekday === day && lesson >= s.lessonStart && lesson <= s.lessonEnd)
  if (mine && theirs) {
    const sameRoom = mySchedule.some(
      (s) => s.weekday === day && lesson >= s.lessonStart && lesson <= s.lessonEnd &&
        theirSchedule.some((t) => t.weekday === day && t.location === s.location),
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
  const result: { day: string; slots: string }[] = []
  for (let d = 0; d < 7; d++) {
    const free = grid.value[d].lessons
      .map((k, i) => (k === 'both-free' ? i + 1 : null))
      .filter((n): n is number => n !== null)
    if (free.length) result.push({ day: days[d], slots: `第 ${free.join('、')} 节` })
  }
  return result
})

const cellStyle: Record<CellKind, string> = {
  'both-busy': 'bg-blush/30 text-blush',
  'one-busy': 'bg-primary-100 text-primary-400',
  'both-free': 'bg-emerald-100 text-emerald-600',
  'same-room': 'bg-amber-100 text-amber-600',
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
    <div v-if="step === 1" class="mt-8 glass-card p-8 max-w-2xl">
      <div
        class="border-2 border-dashed rounded-xl2 p-14 text-center transition cursor-pointer"
        :class="uploaded ? 'border-emerald-300 bg-emerald-50/50' : 'border-primary-200 hover:border-primary-400'"
        @click="handleDrop"
        @dragover.prevent
        @drop.prevent="handleDrop"
      >
        <div v-if="fileParsing" class="flex flex-col items-center">
          <div class="w-10 h-10 border-4 border-primary-200 border-t-primary rounded-full animate-spin"></div>
          <p class="mt-4 text-sm text-sub">正在解析课表…</p>
        </div>
        <div v-else-if="uploaded" class="flex flex-col items-center">
          <div class="w-14 h-14 rounded-full bg-emerald-100 flex items-center justify-center text-2xl">✓</div>
          <p class="mt-3 text-ink font-medium">课表解析完成</p>
          <p class="mt-1 text-xs text-faint">共解析到 {{ mySchedule.length }} 门课程</p>
        </div>
        <div v-else class="flex flex-col items-center">
          <div class="w-14 h-14 rounded-full bg-primary-50 flex items-center justify-center text-3xl text-primary">📅</div>
          <p class="mt-4 text-ink">拖拽课表文件到这里，或点击选择</p>
          <p class="mt-1 text-sm text-faint">支持 .ics 文件 或 浙理工教务系统导出的 PDF</p>
        </div>
      </div>

      <div v-if="uploaded && !fileParsing" class="mt-6">
        <h3 class="text-sm font-medium text-sub mb-3">解析出的课程预览</h3>
        <div class="space-y-2 max-h-56 overflow-auto">
          <div v-for="(c, i) in mySchedule" :key="i" class="flex items-center gap-3 text-sm bg-white/60 rounded-lg px-3 py-2">
            <span class="text-faint text-xs w-8">{{ days[c.weekday] }}</span>
            <span class="text-ink flex-1">{{ c.name }}</span>
            <span class="text-faint text-xs">{{ c.location }} · {{ c.lessonStart }}-{{ c.lessonEnd }} 节</span>
          </div>
        </div>
        <div class="mt-6">
          <button class="btn-primary w-full" @click="step = 2">下一步：选择对比对象</button>
        </div>
      </div>
    </div>

    <!-- Step 2 -->
    <div v-else-if="step === 2" class="mt-8 glass-card p-8 max-w-2xl">
      <label class="label">搜索圈友昵称</label>
      <input v-model="chosenName" class="input" placeholder="输入昵称，例如：摩卡" />

      <div v-if="chosenName" class="mt-4">
        <div
          v-for="m in members.filter((x) => x.displayName.includes(chosenName) || x.username.includes(chosenName))"
          :key="m.id"
          class="flex items-center gap-3 p-3 rounded-xl hover:bg-primary-50 cursor-pointer transition"
          :class="chosen?.id === m.id ? 'bg-primary-50 ring-2 ring-primary-300' : ''"
          @click="chosenName = m.displayName"
        >
          <UserAvatar :name="m.displayName" :size="40" />
          <div class="flex-1">
            <p class="text-sm text-ink font-medium">{{ m.displayName }}</p>
            <p class="text-xs text-faint">@{{ m.username }}</p>
          </div>
          <span v-if="chosen?.id === m.id" class="text-primary font-medium text-sm">已选 ✓</span>
        </div>
      </div>

      <div class="mt-6 bg-primary-50 rounded-xl p-4 text-sm text-primary-800">
        也可以「用链接分享我的课表给对方」，对方打开链接后即可查看对比结果。
      </div>

      <div class="mt-6 flex gap-3">
        <button class="btn-ghost flex-1" @click="step = 1">上一步</button>
        <button class="btn-primary flex-1" :disabled="!chosen" :class="{ 'opacity-50 cursor-not-allowed': !chosen }" @click="step = 3">
          开始对比
        </button>
      </div>
    </div>

    <!-- Step 3 -->
    <div v-else class="mt-8">
      <div class="glass-card p-8">
        <div class="flex flex-wrap items-center gap-4">
          <div class="flex items-center gap-2">
            <UserAvatar :name="'我'" :size="32" />
            <span class="text-sm text-ink font-medium">我</span>
          </div>
          <span class="text-faint">vs</span>
          <div class="flex items-center gap-2">
            <UserAvatar :name="chosen?.displayName ?? ''" :size="32" />
            <span class="text-sm text-ink font-medium">{{ chosen?.displayName }}</span>
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
                {{ cellKind(d - 1, lesson) === 'both-free' ? '·' : '' }}
              </div>
            </div>
          </div>
        </div>

        <!-- 推荐空闲时段 -->
        <div class="mt-8">
          <h3 class="text-sm font-semibold text-ink mb-3">推荐空闲时段</h3>
          <div class="space-y-2">
            <div v-for="f in freeSlots" :key="f.day" class="flex items-center gap-3 text-sm bg-emerald-50 rounded-lg px-4 py-2.5">
              <span class="text-emerald-700 font-medium w-12">{{ f.day }}</span>
              <span class="text-emerald-700">{{ f.slots }}</span>
            </div>
          </div>
          <p class="mt-4 text-xs text-faint">以上时段双方都无课，快约起来吧～</p>
        </div>
      </div>
    </div>
  </div>
</template>