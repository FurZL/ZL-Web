<script setup lang="ts">
import { useDialog } from '@/composables/useDialog'

const { toast, confirmState, confirmYes, confirmNo } = useDialog()
</script>

<template>
  <!-- Toast 消息提示 -->
  <Teleport to="body">
    <transition name="toast">
      <div
        v-if="toast.visible"
        class="fixed top-20 left-1/2 -translate-x-1/2 z-[300] px-6 py-3 rounded-xl2 bg-ink text-white text-sm shadow-glass"
      >
        {{ toast.message }}
      </div>
    </transition>
  </Teleport>

  <!-- 确认弹窗 -->
  <Teleport to="body">
    <div
      v-if="confirmState.visible"
      class="fixed inset-0 z-[300] bg-black/40 flex items-center justify-center p-4"
      @click.self="confirmNo"
    >
      <div class="glass-card p-6 w-full max-w-sm">
        <p class="text-ink text-sm leading-relaxed">{{ confirmState.message }}</p>
        <div class="mt-6 flex gap-3">
          <button class="btn-ghost flex-1 !py-2 text-sm" @click="confirmNo">取消</button>
          <button class="btn-primary flex-1 !py-2 text-sm" @click="confirmYes">确定</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translate(-50%, -12px);
}
</style>
