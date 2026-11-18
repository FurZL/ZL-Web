/**
 * 刷新页面后的登录态恢复。
 * 路由守卫会在需要登录时先 await 它，否则直链打开受保护页面会被误判为未登录。
 * 只执行一次：并发调用共享同一个 Promise。
 */
import { ensureAccessToken } from './client'
import { hasSessionMarker } from './token'
import { useAuthStore } from '@/stores/auth'

let pending: Promise<void> | null = null
let done = false

export function bootstrapAuth(): Promise<void> {
  if (done) return Promise.resolve()
  if (pending) return pending

  pending = (async () => {
    if (!hasSessionMarker()) return
    try {
      const token = await ensureAccessToken()
      if (!token) return
      await useAuthStore().fetchMe()
    } catch {
      // 刷新失败则保持未登录
    }
  })().finally(() => {
    done = true
    pending = null
  })

  return pending
}
