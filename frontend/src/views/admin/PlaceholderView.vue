<script setup lang="ts">
defineProps<{
  title: string
  desc: string
}>()
</script>

<template>
  <div>
    <h1 class="text-2xl font-bold text-ink">{{ title }}</h1>
    <p class="mt-1 text-sm text-sub">{{ desc }}</p>
    <div class="mt-8 glass-card p-12 text-center">
      <div class="text-4xl">🚧</div>
      <p class="mt-3 text-ink font-medium">该模块正在建设中</p>
      <p class="mt-1 text-sm text-sub">后续版本会逐步开放</p>
    </div>
  </div>
</template>