<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>

<template>
  <section class="max-w-6xl mx-auto px-4 py-16 text-center">
    <h1 class="text-4xl font-bold text-primary">浙江理工福瑞圈</h1>
    <p class="mt-4 text-neutral-600">
      面向 ZJUT Furry 社群的门户、图片展示、成员空间、课表工具与活动平台
    </p>
    <div class="mt-8 flex justify-center gap-4">
      <RouterLink to="/gallery" class="px-6 py-2 bg-primary text-white rounded-lg">
        浏览相册
      </RouterLink>
      <RouterLink to="/schedule" class="px-6 py-2 border border-primary text-primary rounded-lg">
        课表工具
      </RouterLink>
    </div>
  </section>
</template>