import { ref } from 'vue'
import { getPublicConfig } from '@/api/site'

const siteName = ref('啫喱小站')
const siteSubtitle = ref('温暖、可爱、有社群感的同好之家')
let fetched = false

export async function fetchSiteConfig() {
  if (fetched) return
  try {
    const cfg = await getPublicConfig()
    if (cfg.site_name) {
      siteName.value = cfg.site_name
      document.title = cfg.site_name
    }
    if (cfg.site_subtitle) {
      siteSubtitle.value = cfg.site_subtitle
    }
  } catch {
    // 保持默认值
  }
  fetched = true
}

export function useSiteConfig() {
  return { siteName, siteSubtitle }
}
