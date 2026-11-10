/** 全局对话框：Toast 消息提示 + Confirm 确认弹窗，替代 alert/confirm。 */
import { reactive } from 'vue'

interface ToastState {
  message: string
  visible: boolean
}

interface ConfirmState {
  message: string
  visible: boolean
  resolve: ((value: boolean) => void) | null
}

const toast = reactive<ToastState>({ message: '', visible: false })
const confirmState = reactive<ConfirmState>({ message: '', visible: false, resolve: null })

let toastTimer: ReturnType<typeof setTimeout> | null = null

/** 显示轻量消息提示（替代 alert），约 3 秒自动消失。 */
export function showToast(message: string) {
  toast.message = message
  toast.visible = true
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => {
    toast.visible = false
  }, 3000)
}

/** 显示确认弹窗（替代 confirm），返回 Promise<boolean>。 */
export function showConfirm(message: string): Promise<boolean> {
  return new Promise((resolve) => {
    confirmState.message = message
    confirmState.visible = true
    confirmState.resolve = resolve
  })
}

function resolveConfirm(value: boolean) {
  confirmState.resolve?.(value)
  confirmState.visible = false
  confirmState.resolve = null
}

export function useDialog() {
  return {
    toast,
    confirmState,
    showToast,
    showConfirm,
    confirmYes: () => resolveConfirm(true),
    confirmNo: () => resolveConfirm(false),
  }
}
