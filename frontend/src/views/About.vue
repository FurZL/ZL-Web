<script setup lang="ts">
import { onMounted, ref } from 'vue'
import ImagePlaceholder from '@/components/ImagePlaceholder.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import { getClubIntro } from '@/api/site'
import { useAuthStore } from '@/stores/auth'
import { request } from '@/api/client'
import type { ClubIntro, MemberProfile } from '@/types'

const auth = useAuthStore()
const members = ref<MemberProfile[]>([])

const intro = ref<ClubIntro>({ title: '关于我们', content: '' })
const loading = ref(true)

onMounted(async () => {
  try {
    intro.value = await getClubIntro()
  } catch {
    // 用默认值
  } finally {
    loading.value = false
  }
  // 加载公开成员列表
  try {
    const data = await request<{ items: MemberProfile[] }>({ method: 'GET', url: '/profile/members' })
    members.value = data.items
  } catch {
    // 成员加载失败不阻断页面
  }
})

const timeline = [
  { year: '2023', title: '社团成立', desc: '一群喜欢毛茸茸的伙伴聚在了一起，福瑞圈正式成立。' },
  { year: '2024', title: '第一次漫展', desc: '第一次以社团名义参加漫展，结识了更多同好。' },
  { year: '2025', title: '成员破百', desc: '社团成员超过一百人，日常活动更加丰富。' },
  { year: '2026', title: '线上平台上线', desc: '有了自己的网站，分享照片、约时间更方便。' },
]
</script>

<template>
  <div class="max-w-6xl mx-auto px-4 py-12">
    <!-- 头部 -->
    <div class="text-center max-w-2xl mx-auto">
      <h1 class="text-3xl md:text-4xl font-bold text-ink">关于我们</h1>
      <p class="mt-4 text-sub leading-relaxed">
        浙江理工福瑞圈，一个温暖、可爱、有社群感的 Furry 同好之家。
      </p>
    </div>

    <!-- 社团故事 -->
    <div class="mt-12 glass-card p-8 md:p-12 grid md:grid-cols-2 gap-8 items-center">
      <div>
        <h2 class="text-xl font-bold text-ink">{{ intro.title || '我们的故事' }}</h2>
        <div v-if="loading" class="mt-4 space-y-2">
          <div class="h-4 bg-primary-100 rounded animate-pulse"></div>
          <div class="h-4 bg-primary-100 rounded animate-pulse w-3/4"></div>
        </div>
        <div v-else-if="intro.content" class="mt-4 text-sub leading-relaxed whitespace-pre-wrap">{{ intro.content }}</div>
        <div v-else>
          <p class="mt-4 text-sub leading-relaxed">
            从几位喜欢毛茸茸角色与创作的伙伴开始，我们在校园里慢慢聚集起了更多同好。
            一起看展、一起画画、一起记录生活的美好，也互相陪伴成为更好的自己。
          </p>
          <p class="mt-3 text-sub leading-relaxed">
            我们希望这里是一个所有人都能被温柔对待的地方——不论你是谁，喜欢什么，这里都有你的位置。
          </p>
        </div>
      </div>
      <ImagePlaceholder title="社团大合照" aspect="4/3" />
    </div>

    <!-- 成员展示 -->
    <div class="mt-12">
      <h2 class="text-xl font-bold text-ink mb-6">可爱的大家</h2>
      <div class="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div v-for="m in members" :key="m.id" class="glass-card p-5 text-center hover:shadow-soft transition">
            <div class="flex justify-center">
              <UserAvatar :name="m.display_name" :size="56" />
            </div>
            <p class="mt-3 text-sm font-medium text-ink">{{ m.display_name }}</p>
            <p class="text-xs text-faint mt-0.5">{{ m.bio || '这位同学还没有写简介' }}</p>
          </div>
      </div>
    </div>

    <!-- 活动时间线 -->
    <div class="mt-12">
      <h2 class="text-xl font-bold text-ink mb-6">成长时间线</h2>
      <div class="relative pl-6 border-l-2 border-primary-100 space-y-8">
        <div v-for="t in timeline" :key="t.year" class="relative">
          <span class="absolute -left-[31px] top-1 w-4 h-4 rounded-full bg-primary shadow-glow"></span>
          <div class="glass-card p-5">
            <div class="flex items-center gap-3">
              <span class="text-primary-700 font-bold">{{ t.year }}</span>
              <h3 class="font-semibold text-ink">{{ t.title }}</h3>
            </div>
            <p class="mt-2 text-sm text-sub">{{ t.desc }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 加入方式（仅未登录显示） -->
    <div v-if="!auth.isLoggedIn" class="mt-12 glass-card p-8 text-center max-w-2xl mx-auto">
      <h2 class="text-xl font-bold text-ink">怎么加入我们？</h2>
      <p class="mt-3 text-sub text-sm leading-relaxed">
        点击注册，填写基本信息并提交申请。管理员审批通过后即可登录，开始你的毛茸茸之旅～
      </p>
      <RouterLink to="/register" class="mt-6 inline-flex items-center gap-1.5 text-sm font-medium text-primary-700 bg-primary/10 border border-primary/20 hover:bg-primary/20 rounded-full px-5 py-2 transition">去注册</RouterLink>
    </div>
  </div>
</template>