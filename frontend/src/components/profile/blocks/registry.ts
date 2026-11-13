/** 区块白名单：渲染器与编辑器共用这一份，避免两处漂移 */
import type { Component } from 'vue'
import type { ProfileBlock, ProfileBlockType, ProfileSpan } from '@/types'
import BioBlock from './BioBlock.vue'
import QuoteBlock from './QuoteBlock.vue'
import FeaturedPhotoBlock from './FeaturedPhotoBlock.vue'
import PhotoWallBlock from './PhotoWallBlock.vue'
import GalleryLinkBlock from './GalleryLinkBlock.vue'
import LinksBlock from './LinksBlock.vue'
import StatsBlock from './StatsBlock.vue'
import SandboxBlock from './SandboxBlock.vue'

export const BLOCK_COMPONENTS: Record<ProfileBlockType, Component> = {
  bio: BioBlock,
  quote: QuoteBlock,
  featured_photo: FeaturedPhotoBlock,
  photo_wall: PhotoWallBlock,
  gallery_link: GalleryLinkBlock,
  links: LinksBlock,
  stats: StatsBlock,
  html_block: SandboxBlock,
}

export const BLOCK_LABELS: Record<ProfileBlockType, string> = {
  bio: '个人简介',
  quote: '一句话',
  featured_photo: '主图',
  photo_wall: '照片墙',
  gallery_link: '图库入口',
  links: '链接组',
  stats: '数据卡',
  html_block: '自定义 HTML',
}

export const BLOCK_ICONS: Record<ProfileBlockType, string> = {
  bio: '📝',
  quote: '❝',
  featured_photo: '🖼',
  photo_wall: '🧩',
  gallery_link: '🔗',
  links: '📎',
  stats: '📊',
  html_block: '</>',
}

/** 每种类型允许的宽度；顺序即属性面板里按钮的顺序 */
export const ALLOWED_SPANS: Record<ProfileBlockType, ProfileSpan[]> = {
  bio: [4, 6, 8, 12],
  quote: [4, 6, 12],
  featured_photo: [12],
  photo_wall: [6, 8, 12],
  gallery_link: [3, 4, 6, 12],
  links: [3, 4, 6],
  stats: [3, 4, 6, 12],
  html_block: [12],
}

export const DEFAULT_SPAN: Record<ProfileBlockType, ProfileSpan> = {
  bio: 8,
  quote: 6,
  featured_photo: 12,
  photo_wall: 6,
  gallery_link: 4,
  links: 4,
  stats: 6,
  html_block: 12,
}

/**
 * Tailwind 只认源码里的字面量类名，`col-span-${n}` 在生产构建会被清掉。
 * 这里的每个值都必须是完整字符串。
 */
export const SPAN_CLASS: Record<ProfileSpan, string> = {
  3: 'col-span-12 md:col-span-3',
  4: 'col-span-12 md:col-span-4',
  6: 'col-span-12 md:col-span-6',
  8: 'col-span-12 md:col-span-8',
  12: 'col-span-12 md:col-span-12',
}

/** 这些块自己铺满卡片，渲染器不再加内边距与卡片表面 */
export const FLUSH_TYPES: ReadonlySet<ProfileBlockType> = new Set<ProfileBlockType>(['html_block'])

export function isBlockType(value: string): value is ProfileBlockType {
  return Object.prototype.hasOwnProperty.call(BLOCK_COMPONENTS, value)
}

export function normalizeSpan(type: ProfileBlockType, span: unknown): ProfileSpan {
  const allowed = ALLOWED_SPANS[type]
  const n = typeof span === 'number' ? span : Number(span)
  return allowed.includes(n as ProfileSpan) ? (n as ProfileSpan) : DEFAULT_SPAN[type]
}

let counter = 0

/** 客户端生成，服务端只校验 [A-Za-z0-9_-]{1,32} 与同一布局内唯一 */
export function newBlockId(): string {
  counter = (counter + 1) % 46656
  return `b${Date.now().toString(36).slice(-5)}${counter.toString(36).padStart(2, '0')}`
}

export function defaultProps(type: ProfileBlockType): Record<string, unknown> {
  switch (type) {
    case 'bio':
      return { text: '' }
    case 'quote':
      return { text: '', author: '' }
    case 'featured_photo':
      return { object_key: '', caption: '' }
    case 'photo_wall':
      return { object_keys: [], columns: 3 }
    case 'gallery_link':
      return { tag: '', label: '去看图' }
    case 'links':
      return { items: [] }
    case 'stats':
      return { items: ['joined_days', 'gallery_image_count'] }
    case 'html_block':
      return { html: '', height: 200 }
  }
}

export function newBlock(type: ProfileBlockType): ProfileBlock {
  return {
    id: newBlockId(),
    type,
    span: DEFAULT_SPAN[type],
    props: defaultProps(type),
  }
}
