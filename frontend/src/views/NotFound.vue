<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>

<template>
  <div class="max-w-md mx-auto px-4 py-24 text-center">
    <div class="text-7xl font-bold text-primary-200">404</div>
    <h1 class="mt-4 text-2xl font-bold text-ink">页面走丢啦</h1>
    <p class="mt-2 text-sub text-sm">你访问的页面不存在，可能已经被移动或删除。</p>
    <RouterLink to="/" class="btn-primary mt-8 inline-flex">回到首页</RouterLink>
  </div>
</template>