<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import UserAvatar from '@/components/UserAvatar.vue'
import ImagePlaceholder from '@/components/ImagePlaceholder.vue'
import { members } from '@/api/mock'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const auth = useAuthStore()

const isSelf = computed(() => !route.params.username)
const profile = computed(() => {
  if (isSelf.value) return auth.user
  const uname = route.params.username as string
  return members.find((m) => m.username === uname || m.displayName === uname) ?? null
})

const privatePhotos = [
  { id: '1', title: '生日聚会留影', date: '2026-10-01' },
  { id: '2', title: '和摩卡的合照', date: '2026-09-20' },
  { id: '3', title: '新买的毛绒玩偶', date: '2026-11-05' },
  { id: '4', title: '社团活动的我', date: '2026-08-30' },
]
</script>

<template>
  <div class="max-w-6xl mx-auto px-4 py-10">
    <!-- 资料卡 -->
    <div class="glass-card p-8">
      <div class="flex flex-col sm:flex-row items-center gap-6">
        <UserAvatar :name="profile?.displayName ?? '?'" :size="84" />
        <div class="text-center sm:text-left flex-1">
          <div class="flex items-center justify-center sm:justify-start gap-3">
            <h1 class="text-2xl font-bold text-ink">{{ profile?.displayName }}</h1>
            <span class="text-xs font-medium text-primary-700 bg-primary-100 rounded-full px-2.5 py-0.5">@{{ profile?.username }}</span>
          </div>
          <p class="mt-2 text-sub text-sm max-w-md">{{ profile?.bio }}</p>
        </div>
        <button v-if="isSelf" class="btn-ghost !px-5 !py-2">编辑资料</button>
        <RouterLink v-else to="/schedule" class="btn-primary !px-5 !py-2">发起课表对比</RouterLink>
      </div>
    </div>

    <!-- 自己的视角：私有相册 + 课表 -->
    <template v-if="isSelf">
      <div class="mt-10 flex items-center justify-between">
        <h2 class="text-lg font-semibold text-ink">我的私有相册</h2>
        <span class="text-xs text-faint">仅自己可见</span>
      </div>
      <div class="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
        <div v-for="p in privatePhotos" :key="p.id" class="glass-card p-2 group relative">
          <div class="rounded-xl overflow-hidden">
            <ImagePlaceholder :title="p.title" aspect="1/1" />
          </div>
          <div class="px-2 py-2 flex items-center justify-between">
            <div class="min-w-0">
              <p class="text-sm text-ink truncate">{{ p.title }}</p>
              <p class="text-xs text-faint">{{ p.date }}</p>
            </div>
            <button class="text-faint hover:text-blush shrink-0 opacity-0 group-hover:opacity-100 transition" title="删除">🗑</button>
          </div>
        </div>
        <button class="border-2 border-dashed border-primary-200 rounded-xl2 flex flex-col items-center justify-center gap-2 text-primary-400 hover:border-primary-400 hover:text-primary-600 transition min-h-[160px]">
          <span class="text-2xl">＋</span>
          <span class="text-sm">上传图片</span>
        </button>
      </div>

      <div class="mt-10 flex items-center justify-between">
        <h2 class="text-lg font-semibold text-ink">我的课表</h2>
        <button class="text-sm text-primary-700 hover:underline">删除</button>
      </div>
      <div class="mt-4 glass-card p-6 flex items-center gap-4">
        <div class="w-12 h-12 rounded-xl bg-primary-50 flex items-center justify-center text-2xl">📅</div>
        <div class="flex-1">
          <p class="text-sm text-ink font-medium">已上传课表</p>
          <p class="text-xs text-faint">2026-2027 第一学期 · 解析于 2026-11-09</p>
        </div>
        <RouterLink to="/schedule" class="btn-ghost !px-4 !py-2 text-sm">去对比</RouterLink>
      </div>
    </template>

    <!-- 他人视角 -->
    <template v-else>
      <div class="mt-10">
        <h2 class="text-lg font-semibold text-ink">公开介绍</h2>
        <p class="mt-2 text-sub leading-relaxed max-w-2xl">这位圈友还没有填写更多公开介绍。</p>
      </div>
      <div class="mt-10 glass-card p-8 text-center">
        <div class="w-14 h-14 mx-auto rounded-full bg-primary-50 flex items-center justify-center text-2xl">🔒</div>
        <p class="mt-4 text-ink font-medium">私有相册不可见</p>
        <p class="mt-1 text-sm text-sub">别人看不到 TA 的私有图片</p>
      </div>
    </template>
  </div>
</template>

