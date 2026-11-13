/** 个人主页主题：theme 对象 → 内联样式 / CSS 变量 */
import type { ProfileTheme } from '@/types'

export const DEFAULT_THEME: ProfileTheme = {
  primary: '#6B5CE7',
  accent: '#F0A6C8',
  background_type: 'gradient',
  background_key: null,
  background_blur: 0,
  card_style: 'glass',
}

export interface ThemePreset {
  id: string
  name: string
  primary: string
  accent: string
  background_type: ProfileTheme['background_type']
  background_blur: number
  card_style: ProfileTheme['card_style']
}

// 预设只写入解析后的字段，主题对象里不存在 preset 字段
export const THEME_PRESETS: ThemePreset[] = [
  {
    id: 'violet',
    name: '紫罗兰',
    primary: '#6B5CE7',
    accent: '#F0A6C8',
    background_type: 'gradient',
    background_blur: 0,
    card_style: 'glass',
  },
  {
    id: 'mint',
    name: '薄荷',
    primary: '#2FB89A',
    accent: '#9ED9F0',
    background_type: 'gradient',
    background_blur: 0,
    card_style: 'glass',
  },
  {
    id: 'sunset',
    name: '日落',
    primary: '#E4703F',
    accent: '#F2C14E',
    background_type: 'solid',
    background_blur: 0,
    card_style: 'solid',
  },
  {
    id: 'ink',
    name: '墨蓝',
    primary: '#2E4670',
    accent: '#7C9CC4',
    background_type: 'solid',
    background_blur: 0,
    card_style: 'outline',
  },
  {
    id: 'sakura',
    name: '樱粉',
    primary: '#D9558C',
    accent: '#F5BFD4',
    background_type: 'gradient',
    background_blur: 0,
    card_style: 'glass',
  },
]

const HEX_RE = /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/

function parseHex(hex: string): [number, number, number] | null {
  if (!HEX_RE.test(hex)) return null
  let body = hex.slice(1)
  if (body.length === 3) body = body.split('').map((c) => c + c).join('')
  const n = Number.parseInt(body, 16)
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255]
}

/** 浅色底上做半透明混色；非法色值退回默认主色，不抛错 */
export function tint(hex: string, alpha: number): string {
  const rgb = parseHex(hex)
  if (!rgb) return tint(DEFAULT_THEME.primary, alpha)
  return `rgba(${rgb[0]}, ${rgb[1]}, ${rgb[2]}, ${alpha})`
}

/** 注入到主页容器上的 CSS 变量，块组件内部引用而不依赖 Tailwind 生成动态色 */
export function themeVars(theme: ProfileTheme): Record<string, string> {
  return {
    '--profile-primary': theme.primary,
    '--profile-accent': theme.accent,
    '--profile-primary-soft': tint(theme.primary, 0.12),
    '--profile-accent-soft': tint(theme.accent, 0.2),
  }
}

/** 页面背景；image 类型由渲染器额外铺一层 <img> 并应用 blur */
export function backgroundStyle(theme: ProfileTheme): Record<string, string> {
  if (theme.background_type === 'gradient') {
    return {
      background: `linear-gradient(160deg, ${tint(theme.primary, 0.22)} 0%, #F4F3FB 48%, ${tint(
        theme.accent,
        0.24,
      )} 100%)`,
    }
  }
  if (theme.background_type === 'solid') {
    return { background: tint(theme.primary, 0.1) }
  }
  return { background: '#F4F3FB' }
}

/** 每个块外层卡片的表面样式 */
export function cardSurface(theme: ProfileTheme): Record<string, string> {
  if (theme.card_style === 'solid') {
    return {
      background: '#FFFFFF',
      border: '1px solid rgba(31, 27, 51, 0.06)',
      boxShadow: '0 8px 30px rgba(107, 92, 231, 0.08)',
      borderRadius: '1.25rem',
    }
  }
  if (theme.card_style === 'outline') {
    return {
      background: 'transparent',
      border: `1.5px solid ${tint(theme.primary, 0.45)}`,
      borderRadius: '1.25rem',
    }
  }
  return {
    background: 'rgba(255, 255, 255, 0.72)',
    border: '1px solid rgba(255, 255, 255, 0.6)',
    backdropFilter: 'blur(16px)',
    WebkitBackdropFilter: 'blur(16px)',
    boxShadow: '0 8px 24px rgba(31, 27, 51, 0.06)',
    borderRadius: '1.25rem',
  }
}

/** image 背景图层的模糊；0 表示不加滤镜，避免无意义合成层 */
export function imageLayerStyle(theme: ProfileTheme): Record<string, string> {
  if (theme.background_blur <= 0) return { objectFit: 'cover' }
  return {
    objectFit: 'cover',
    filter: `blur(${theme.background_blur}px)`,
    transform: 'scale(1.08)',
  }
}
