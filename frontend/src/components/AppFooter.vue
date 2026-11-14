<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getFooter } from '@/api/site'
import { useSiteConfig } from '@/composables/useSiteConfig'
import type { FooterConfig } from '@/types'

const { siteName, siteSubtitle } = useSiteConfig()
const year = new Date().getFullYear()
const footer = ref<FooterConfig | null>(null)

onMounted(async () => {
  try {
    footer.value = await getFooter()
  } catch {
    // 用默认值
  }
})
</script>

<template>
  <footer class="mt-16 bg-white/60 backdrop-blur-xl border-t border-white/60">
    <div class="max-w-6xl mx-auto px-4 py-10">
      <div class="flex flex-col md:flex-row items-center justify-between gap-6">
        <div class="flex items-center gap-2.5">
          <img
            src="/logo-m-96.png"
            :alt="siteName"
            width="40"
            height="40"
            class="w-10 h-10 rounded-xl object-contain bg-white/80 border border-white/60 shadow-soft"
          />
          <div>
            <p class="text-sm font-medium text-ink">{{ footer?.copyright_owner ?? siteName }}</p>
            <p class="text-xs text-faint">{{ siteSubtitle }}</p>
          </div>
        </div>
        <div class="flex flex-wrap justify-center gap-x-5 gap-y-2 text-xs text-sub">
          <a
            v-for="link in (footer?.links ?? [])"
            :key="link.label"
            class="hover:text-primary-700 transition"
            :href="link.href"
          >
            {{ link.label }}
          </a>
        </div>
      </div>
      <div class="mt-8 pt-6 border-t border-primary-100/60 text-center text-xs text-faint space-y-1">
        <p>© {{ year }} {{ footer?.copyright_owner ?? siteName }} · All Rights Reserved</p>
        <p v-if="footer?.icp_number || footer?.police_number">
          <span v-if="footer?.icp_number">{{ footer.icp_number }}</span>
          <span v-if="footer?.icp_number && footer?.police_number"> | </span>
          <span v-if="footer?.police_number">{{ footer.police_number }}</span>
        </p>
      </div>
    </div>
  </footer>
</template>
