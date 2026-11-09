<script setup lang="ts">
// 页脚内容由后端 /site/footer 配置动态生成，这里用占位。
const year = new Date().getFullYear()
</script>

<template>
  <footer class="mt-16 bg-white/60 backdrop-blur-xl border-t border-white/60">
    <div class="max-w-6xl mx-auto px-4 py-10">
      <div class="flex flex-col md:flex-row items-center justify-between gap-6">
        <div class="flex items-center gap-2">
          <span class="w-8 h-8 rounded-xl bg-hero-gradient flex items-center justify-center text-white font-bold">福</span>
          <div>
            <p class="text-sm font-medium text-ink">浙江理工福瑞圈</p>
            <p class="text-xs text-faint">温暖、可爱、有社群感的 Furry 之家</p>
          </div>
        </div>
        <div class="flex flex-wrap justify-center gap-x-5 gap-y-2 text-xs text-sub">
          <a class="hover:text-primary-700 transition" href="#">用户协议</a>
          <a class="hover:text-primary-700 transition" href="#">隐私政策</a>
          <a class="hover:text-primary-700 transition" href="#">版权声明</a>
          <a class="hover:text-primary-700 transition" href="#">联系我们</a>
        </div>
      </div>
      <div class="mt-8 pt-6 border-t border-primary-100/60 text-center text-xs text-faint space-y-1">
        <p>© {{ year }} 浙江理工福瑞圈 · All Rights Reserved</p>
        <p>ICP备案号（如有） | 公安联网备案（如有）</p>
      </div>
    </div>
  </footer>
</template>