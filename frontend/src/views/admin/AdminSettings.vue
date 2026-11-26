<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import {
  getAdminSettings,
  getClubIntro,
  updateClubIntro,
  upsertSetting,
} from '@/api/site'
import { useSiteConfig } from '@/composables/useSiteConfig'
import type { SiteSettingRecord } from '@/types'

const tab = ref<'intro' | 'config' | 'footer' | 'legal' | 'registration' | 'oauth'>('intro')
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const { siteName, siteSubtitle } = useSiteConfig()
const successMsg = ref('')

// 社团介绍
const intro = reactive({ title: '关于我们', content: '' })

// 公开配置
const config = reactive({
  site_name: siteName,
  site_subtitle: siteSubtitle,
  logo_url: '',
  favicon_url: '',
})

// 页脚
const footer = reactive({
  copyright_owner: siteName,
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

// 注册设置
const registration = reactive({
  registration_enabled: true,
  require_email_verification: true,
  require_phone_verification: true,
})

const oauth = reactive({
  enabled: false,
  qq_enabled: false,
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
    const reg = settingsData.items.find((s) => s.key === 'registration_config')?.value as Record<string, boolean> | undefined
    if (reg) {
      registration.registration_enabled = reg.registration_enabled ?? true
      registration.require_email_verification = reg.require_email_verification ?? true
      registration.require_phone_verification = reg.require_phone_verification ?? true
    }
    const oauthCfg = settingsData.items.find((s) => s.key === 'oauth_config')?.value as Record<string, boolean> | undefined
    if (oauthCfg) {
      oauth.enabled = oauthCfg.enabled ?? false
      oauth.qq_enabled = oauthCfg.qq_enabled ?? false
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

async function saveRegistration() {
  saving.value = true
  error.value = ''
  try {
    await upsertSetting({
      key: 'registration_config',
      value: { ...registration },
      category: 'site',
      is_public: true,
    })
    showSuccess('注册设置已保存')
  } catch (e) {
    error.value = e instanceof Error ? e.message : '保存失败'
  } finally {
    saving.value = false
  }
}

async function saveOauth() {
  saving.value = true
  error.value = ''
  try {
    await upsertSetting({
      key: 'oauth_config',
      value: { ...oauth },
      category: 'site',
      is_public: true,
    })
    showSuccess('第三方登录设置已保存')
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
  { key: 'registration', label: '注册设置' },
  { key: 'oauth', label: '第三方登录' },
] as { key: typeof tab.value; label: string }[]
</script>

<template>
  <div>
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-2xl font-bold text-ink">网站设置</h1>
      <RouterLink to="/admin/audit" class="btn-sm">操作审计</RouterLink>
    </div>
    <p class="mt-1 text-sm text-sub">社团介绍、Logo、页脚备案信息、法律链接与注册控制</p>

    <!-- Tab 切换 -->
    <div class="mt-6 flex gap-2 flex-wrap">
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
      <div class="spinner"></div>
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

      <!-- 注册设置 -->
      <div v-else-if="tab === 'registration'" class="glass-card p-6 space-y-6">
        <div>
          <h2 class="text-lg font-semibold text-ink">注册开关</h2>
          <p class="text-sm text-sub mt-1">控制是否允许新用户注册，以及注册时需要验证哪些联系方式。</p>
        </div>

        <!-- 是否开启注册 -->
        <label class="flex items-center justify-between p-4 rounded-xl bg-white/60 border border-white/60 cursor-pointer hover:bg-white/80 transition">
          <div>
            <p class="font-medium text-ink">开启注册</p>
            <p class="text-sm text-sub">关闭后前端注册入口隐藏，后端拒绝注册请求</p>
          </div>
          <input
            v-model="registration.registration_enabled"
            type="checkbox"
            class="w-5 h-5 rounded border-gray-300 text-primary focus:ring-primary"
          />
        </label>

        <!-- 是否开启邮箱验证 -->
        <label class="flex items-center justify-between p-4 rounded-xl bg-white/60 border border-white/60 cursor-pointer hover:bg-white/80 transition">
          <div>
            <p class="font-medium text-ink">要求邮箱验证</p>
            <p class="text-sm text-sub">关闭后注册时无需填写邮箱验证码，但邮箱字段仍然必填</p>
          </div>
          <input
            v-model="registration.require_email_verification"
            type="checkbox"
            class="w-5 h-5 rounded border-gray-300 text-primary focus:ring-primary"
          />
        </label>

        <!-- 是否开启手机验证 -->
        <label class="flex items-center justify-between p-4 rounded-xl bg-white/60 border border-white/60 cursor-pointer hover:bg-white/80 transition">
          <div>
            <p class="font-medium text-ink">要求手机验证</p>
            <p class="text-sm text-sub">关闭后注册时无需填写手机验证码，但手机字段仍然必填</p>
          </div>
          <input
            v-model="registration.require_phone_verification"
            type="checkbox"
            class="w-5 h-5 rounded border-gray-300 text-primary focus:ring-primary"
          />
        </label>

        <button class="btn-primary" :disabled="saving" @click="saveRegistration">
          {{ saving ? '保存中…' : '保存注册设置' }}
        </button>
      </div>

      <!-- 第三方登录 -->
      <div v-else-if="tab === 'oauth'" class="glass-card p-6 space-y-6">
        <div>
          <h2 class="text-lg font-semibold text-ink">第三方登录开关</h2>
          <p class="text-sm text-sub mt-1">控制登录页是否展示第三方登录入口；App ID / App Key 仍从后端环境变量读取。</p>
        </div>

        <label class="flex items-center justify-between p-4 rounded-xl bg-white/60 border border-white/60 cursor-pointer hover:bg-white/80 transition">
          <div>
            <p class="font-medium text-ink">开启第三方登录</p>
            <p class="text-sm text-sub">总开关，关闭后前端登录页隐藏全部第三方入口</p>
          </div>
          <input
            v-model="oauth.enabled"
            type="checkbox"
            class="w-5 h-5 rounded border-gray-300 text-primary focus:ring-primary"
          />
        </label>

        <label class="flex items-center justify-between p-4 rounded-xl bg-white/60 border border-white/60 cursor-pointer hover:bg-white/80 transition">
          <div>
            <p class="font-medium text-ink">QQ 登录</p>
            <p class="text-sm text-sub">在登录页显示「QQ 登录」按钮；登录与绑定均要求先通过拼图验证</p>
          </div>
          <input
            v-model="oauth.qq_enabled"
            type="checkbox"
            class="w-5 h-5 rounded border-gray-300 text-primary focus:ring-primary"
          />
        </label>

        <button class="btn-primary" :disabled="saving" @click="saveOauth">
          {{ saving ? '保存中…' : '保存第三方登录设置' }}
        </button>
      </div>
    </div>
  </div>
</template>
