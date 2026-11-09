<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import {
  getAdminSettings,
  getClubIntro,
  updateClubIntro,
  upsertSetting,
} from '@/api/site'
import type { SiteSettingRecord } from '@/types'

const tab = ref<'intro' | 'config' | 'footer' | 'legal'>('intro')
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const successMsg = ref('')

// 社团介绍
const intro = reactive({ title: '关于我们', content: '' })

// 公开配置
const config = reactive({
  site_name: '浙江理工福瑞圈',
  site_subtitle: '温暖、可爱、有社群感的 Furry 之家',
  logo_url: '',
  favicon_url: '',
})

// 页脚
const footer = reactive({
  copyright_owner: '浙江理工福瑞圈',
  icp_number: '',
  police_number: '',
})

// 法律
const legal = reactive({
  terms_url: '',
  privacy_url: '',
  copyright_notice: '',
  contact_email: '',
})

const allSettings = ref<SiteSettingRecord[]>([])

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [introData, settingsData] = await Promise.all([
      getClubIntro(),
      getAdminSettings(),
    ])
    intro.title = introData.title || '关于我们'
    intro.content = introData.content || ''
    allSettings.value = settingsData.items

    // 从设置中回填各分类
    const cfg = settingsData.items.find((s) => s.key === 'public_config')?.value as Record<string, string> | undefined
    if (cfg) {
      config.site_name = cfg.site_name ?? config.site_name
      config.site_subtitle = cfg.site_subtitle ?? config.site_subtitle
      config.logo_url = cfg.logo_url ?? ''
      config.favicon_url = cfg.favicon_url ?? ''
    }
    const ft = settingsData.items.find((s) => s.key === 'footer')?.value as Record<string, string> | undefined
    if (ft) {
      footer.copyright_owner = ft.copyright_owner ?? footer.copyright_owner
      footer.icp_number = ft.icp_number ?? ''
      footer.police_number = ft.police_number ?? ''
    }
    const lg = settingsData.items.find((s) => s.key === 'legal')?.value as Record<string, string> | undefined
    if (lg) {
      legal.terms_url = lg.terms_url ?? ''
      legal.privacy_url = lg.privacy_url ?? ''
      legal.copyright_notice = lg.copyright_notice ?? ''
      legal.contact_email = lg.contact_email ?? ''
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)

function showSuccess(msg: string) {
  successMsg.value = msg
  setTimeout(() => (successMsg.value = ''), 2500)
}

async function saveIntro() {
  saving.value = true
  error.value = ''
  try {
    await updateClubIntro({ title: intro.title, content: intro.content })
    showSuccess('社团介绍已保存')
  } catch (e) {
    error.value = e instanceof Error ? e.message : '保存失败'
  } finally {
    saving.value = false
  }
}

async function saveConfig() {
  saving.value = true
  error.value = ''
  try {
    await upsertSetting({
      key: 'public_config',
      value: { ...config },
      category: 'site',
      is_public: true,
    })
    showSuccess('公开配置已保存')
  } catch (e) {
    error.value = e instanceof Error ? e.message : '保存失败'
  } finally {
    saving.value = false
  }
}

async function saveFooter() {
  saving.value = true
  error.value = ''
  try {
    await upsertSetting({
      key: 'footer',
      value: { ...footer },
      category: 'site',
      is_public: true,
    })
    showSuccess('页脚配置已保存')
  } catch (e) {
    error.value = e instanceof Error ? e.message : '保存失败'
  } finally {
    saving.value = false
  }
}

async function saveLegal() {
  saving.value = true
  error.value = ''
  try {
    await upsertSetting({
      key: 'legal',
      value: { ...legal },
      category: 'site',
      is_public: true,
    })
    showSuccess('法律信息已保存')
  } catch (e) {
    error.value = e instanceof Error ? e.message : '保存失败'
  } finally {
    saving.value = false
  }
}

const tabs = [
  { key: 'intro', label: '社团介绍' },
  { key: 'config', label: '公开配置' },
  { key: 'footer', label: '页脚信息' },
  { key: 'legal', label: '法律信息' },
] as const
</script>

<template>
  <div>
    <h1 class="text-2xl font-bold text-ink">网站设置</h1>
    <p class="mt-1 text-sm text-sub">社团介绍、Logo、页脚备案信息与法律链接</p>

    <!-- Tab 切换 -->
    <div class="mt-6 flex gap-2">
      <button
        v-for="t in tabs"
        :key="t.key"
        class="text-sm font-medium text-primary-700 rounded-full px-5 py-2 transition"
        :class="tab === t.key ? 'bg-primary/30 border border-primary/30 shadow-glass text-primary-800' : 'bg-primary/5 border border-primary/10 hover:bg-primary/15'"
        @click="tab = t.key"
      >
        {{ t.label }}
      </button>
    </div>

    <!-- 成功/错误提示 -->
    <div v-if="successMsg" class="mt-4 text-sm text-emerald-600 bg-emerald-50 rounded-lg px-4 py-2">{{ successMsg }}</div>
    <div v-if="error" class="mt-4 text-sm text-red-600 bg-red-50 rounded-lg px-4 py-2">{{ error }}</div>

    <div v-if="loading" class="mt-8 glass-card p-12 text-center">
      <div class="w-8 h-8 border-4 border-primary-200 border-t-primary rounded-full animate-spin mx-auto"></div>
      <p class="mt-3 text-sm text-sub">加载中…</p>
    </div>

    <div v-else class="mt-6">
      <!-- 社团介绍 -->
      <div v-if="tab === 'intro'" class="glass-card p-6 space-y-4">
        <div>
          <label class="label">标题</label>
          <input v-model="intro.title" class="input" placeholder="关于我们" />
        </div>
        <div>
          <label class="label">内容（支持换行）</label>
          <textarea v-model="intro.content" class="input min-h-[180px]" rows="8" placeholder="填写社团介绍内容…"></textarea>
        </div>
        <button class="btn-primary" :disabled="saving" @click="saveIntro">
          {{ saving ? '保存中…' : '保存社团介绍' }}
        </button>
      </div>

      <!-- 公开配置 -->
      <div v-else-if="tab === 'config'" class="glass-card p-6 space-y-4">
        <div class="grid sm:grid-cols-2 gap-4">
          <div>
            <label class="label">网站名称</label>
            <input v-model="config.site_name" class="input" />
          </div>
          <div>
            <label class="label">副标题</label>
            <input v-model="config.site_subtitle" class="input" />
          </div>
          <div>
            <label class="label">Logo URL</label>
            <input v-model="config.logo_url" class="input" placeholder="https://..." />
          </div>
          <div>
            <label class="label">Favicon URL</label>
            <input v-model="config.favicon_url" class="input" placeholder="https://..." />
          </div>
        </div>
        <button class="btn-primary" :disabled="saving" @click="saveConfig">
          {{ saving ? '保存中…' : '保存公开配置' }}
        </button>
      </div>

      <!-- 页脚 -->
      <div v-else-if="tab === 'footer'" class="glass-card p-6 space-y-4">
        <div class="grid sm:grid-cols-3 gap-4">
          <div>
            <label class="label">版权主体</label>
            <input v-model="footer.copyright_owner" class="input" />
          </div>
          <div>
            <label class="label">ICP 备案号</label>
            <input v-model="footer.icp_number" class="input" />
          </div>
          <div>
            <label class="label">公安备案号</label>
            <input v-model="footer.police_number" class="input" />
          </div>
        </div>
        <button class="btn-primary" :disabled="saving" @click="saveFooter">
          {{ saving ? '保存中…' : '保存页脚配置' }}
        </button>
      </div>

      <!-- 法律信息 -->
      <div v-else-if="tab === 'legal'" class="glass-card p-6 space-y-4">
        <div class="grid sm:grid-cols-2 gap-4">
          <div>
            <label class="label">用户协议链接</label>
            <input v-model="legal.terms_url" class="input" placeholder="https://..." />
          </div>
          <div>
            <label class="label">隐私政策链接</label>
            <input v-model="legal.privacy_url" class="input" placeholder="https://..." />
          </div>
          <div>
            <label class="label">版权声明</label>
            <input v-model="legal.copyright_notice" class="input" />
          </div>
          <div>
            <label class="label">联系邮箱</label>
            <input v-model="legal.contact_email" class="input" placeholder="contact@example.com" />
          </div>
        </div>
        <button class="btn-primary" :disabled="saving" @click="saveLegal">
          {{ saving ? '保存中…' : '保存法律信息' }}
        </button>
      </div>
    </div>
  </div>
</template>
