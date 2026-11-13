/** 所有区块组件共用同一组 props，这样 `<component :is>` 不需要按类型拼参数 */
import type { ProfileBlock, ProfileMedia, ProfileStats } from '@/types'

export interface BlockProps {
  block: ProfileBlock
  media: Record<string, ProfileMedia>
  stats: ProfileStats
}

export function str(block: ProfileBlock, key: string, fallback = ''): string {
  const v = block.props[key]
  return typeof v === 'string' ? v : fallback
}

export function num(block: ProfileBlock, key: string, fallback: number): number {
  const v = block.props[key]
  return typeof v === 'number' && Number.isFinite(v) ? v : fallback
}

export function strList(block: ProfileBlock, key: string): string[] {
  const v = block.props[key]
  return Array.isArray(v) ? v.filter((x): x is string => typeof x === 'string') : []
}

export const STAT_LABELS: Record<string, { label: string; unit: string }> = {
  joined_days: { label: '加入天数', unit: '天' },
  gallery_image_count: { label: '公开照片', unit: '张' },
}
