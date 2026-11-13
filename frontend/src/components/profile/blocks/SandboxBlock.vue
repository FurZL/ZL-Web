<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { BlockProps } from './types'
import { num, str } from './types'

const props = defineProps<BlockProps>()

const loaded = ref(false)
const html = computed(() => str(props.block, 'html'))
const empty = computed(() => !html.value.trim())

const height = computed(() => {
  const h = num(props.block, 'height', 200)
  return h === 400 || h === 600 ? h : 200
})

// 沙箱内不放开 same-origin：读不到 cookie / localStorage，也调不动本站接口
const CSP =
  "default-src 'none'; img-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; font-src data:"

const srcdoc = computed(
  () =>
    `<meta http-equiv="Content-Security-Policy" content="${CSP}">` +
    '<style>html,body{margin:0;padding:0;font-family:"Noto Sans SC","PingFang SC","Microsoft YaHei",system-ui,sans-serif;color:#1F1B33;}</style>' +
    html.value,
)

watch(
  () => props.block.id,
  () => {
    loaded.value = false
  },
)
</script>

<template>
  <div class="relative w-full overflow-hidden rounded-xl2 bg-primary-50/60" :style="{ height: height + 'px' }">
    <div v-if="empty" class="w-full h-full flex flex-col items-center justify-center gap-1 text-faint">
      <span class="text-2xl">&lt;/&gt;</span>
      <span class="text-xs">这个模块还没有内容</span>
    </div>

    <iframe
      v-else-if="loaded"
      :srcdoc="srcdoc"
      sandbox="allow-scripts"
      referrerpolicy="no-referrer"
      class="w-full h-full border-0 bg-white"
      :title="'自定义内容'"
    ></iframe>

    <button
      v-else
      class="w-full h-full flex flex-col items-center justify-center gap-1.5 text-sub hover:text-ink transition"
      @click="loaded = true"
    >
      <span class="text-lg">▶</span>
      <span class="text-xs">点击加载自定义内容</span>
      <span class="text-[10px] text-faint">在隔离环境中运行</span>
    </button>
  </div>
</template>
