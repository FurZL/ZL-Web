import { fileURLToPath, URL } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { profileMock } from './dev/profileMock'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  // 只有显式打开开关时才挂 mock；普通 dev 与生产构建都不受影响
  const useProfileMock = env.VITE_PROFILE_MOCK === '1'

  return {
    plugins: [vue(), ...(useProfileMock ? [profileMock()] : [])],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: {
      port: 5173,
      strictPort: true,
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
      },
    },
  }
})
