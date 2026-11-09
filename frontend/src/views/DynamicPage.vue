<script setup lang="ts">
import { useRoute } from 'vue-router'
import { computed } from 'vue'

// 动态页面渲染入口：按 slug 拉取页面 Schema，
// 使用白名单组件渲染（hero/rich_text/image/countdown 等），
// 未知组件类型忽略并记录错误。这里先做入口占位。
const route = useRoute()
const slug = computed(() => route.params.slug as string)
</script>

<template>
  <section class="max-w-6xl mx-auto px-4 py-10">
    <h2 class="text-xl font-semibold">动态页面</h2>
    <p class="mt-2 text-neutral-500">slug: {{ slug }}（待接入 /pages/{slug} 与 Schema 渲染器）</p>
  </section>
</template>