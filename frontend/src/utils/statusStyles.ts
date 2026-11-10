/** 全站状态 badge 配色共享常量，避免各组件重复定义 statusMap。 */

export const MODERATION_STATUS: Record<string, { text: string; cls: string }> = {
  pending: { text: '待审核', cls: 'bg-amber-100 text-amber-700' },
  approved: { text: '已通过', cls: 'bg-emerald-100 text-emerald-700' },
  rejected: { text: '已拒绝', cls: 'bg-red-100 text-red-600' },
}

export const EVENT_STATUS: Record<string, { text: string; cls: string }> = {
  draft: { text: '草稿', cls: 'bg-gray-100 text-gray-600' },
  published: { text: '已发布', cls: 'bg-emerald-100 text-emerald-700' },
  cancelled: { text: '已取消', cls: 'bg-red-100 text-red-600' },
}

export const PAGE_STATUS: Record<string, { text: string; cls: string }> = {
  draft: { text: '草稿', cls: 'bg-gray-100 text-gray-600' },
  published: { text: '已发布', cls: 'bg-emerald-100 text-emerald-700' },
  archived: { text: '已归档', cls: 'bg-amber-100 text-amber-700' },
}

export const REG_STATUS: Record<string, { text: string; cls: string }> = {
  registered: { text: '已报名', cls: 'bg-emerald-100 text-emerald-700' },
  waitlisted: { text: '候补', cls: 'bg-amber-100 text-amber-700' },
  cancelled: { text: '已取消', cls: 'bg-gray-100 text-gray-500' },
  checked_in: { text: '已签到', cls: 'bg-primary-100 text-primary-700' },
}

export const ANNOUNCEMENT_STATUS: Record<string, { text: string; cls: string }> = {
  draft: { text: '草稿', cls: 'bg-gray-100 text-gray-600' },
  published: { text: '已发布', cls: 'bg-emerald-100 text-emerald-700' },
  expired: { text: '已过期', cls: 'bg-amber-100 text-amber-700' },
}
