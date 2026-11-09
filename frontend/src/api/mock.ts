import type { Announcement, CourseSlot, GalleryImage, User } from '@/types'

export const currentUser: User = {
  id: 'u-1',
  username: 'fluffy_zjut',
  displayName: '毛球',
  role: 'photographer',
  avatar: '',
  bio: '浙江理工的毛茸茸记录者，喜欢拍校园里的小确幸。',
}

export const members: User[] = [
  currentUser,
  { id: 'u-2', username: 'mocha', displayName: '摩卡', role: 'member', avatar: '', bio: '咖啡与猫。' },
  { id: 'u-3', username: 'aurora', displayName: '极光', role: 'photographer', avatar: '', bio: '用镜头追光。' },
  { id: 'u-4', username: 'pudding', displayName: '布丁', role: 'member', avatar: '', bio: '摸鱼达人。' },
  { id: 'u-5', username: 'sakura', displayName: '小樱', role: 'admin', avatar: '', bio: '社长，负责让大家开心。' },
]

export const galleryImages: GalleryImage[] = [
  { id: 'g1', url: '', title: '秋日校园', tags: ['日常', '校园'], photographer: '极光', width: 800, height: 1067, uploadedAt: '2026-10-12' },
  { id: 'g2', url: '', title: '社团迎新夜', tags: ['活动'], photographer: '毛球', width: 800, height: 600, uploadedAt: '2026-09-28' },
  { id: 'g3', url: '', title: '毛茸茸的午后', tags: ['日常', '治愈'], photographer: '摩卡', width: 800, height: 1000, uploadedAt: '2026-09-15' },
  { id: 'g4', url: '', title: '万圣节派对', tags: ['节日'], photographer: '极光', width: 800, height: 640, uploadedAt: '2026-10-31' },
  { id: 'g5', url: '', title: '图书馆一角', tags: ['校园'], photographer: '毛球', width: 800, height: 800, uploadedAt: '2026-10-05' },
  { id: 'g6', url: '', title: '冬日暖阳', tags: ['日常'], photographer: '布丁', width: 800, height: 1100, uploadedAt: '2026-11-03' },
  { id: 'g7', url: '', title: '社团例会', tags: ['活动', '日常'], photographer: '毛球', width: 800, height: 600, uploadedAt: '2026-10-20' },
  { id: 'g8', url: '', title: '小雨中的钟楼', tags: ['校园', '治愈'], photographer: '极光', width: 800, height: 1050, uploadedAt: '2026-10-08' },
]

export const announcements: Announcement[] = [
  { id: 'a1', title: '十一月社团观影会报名开启', summary: '本周六晚七点，一起看《动物城里》～', date: '2026-11-09', pinned: true },
  { id: 'a2', title: '新成员审批流程提醒', summary: '请已在系统提交申请的圈友耐心等待审核。', date: '2026-11-06', pinned: false },
  { id: 'a3', title: '秋冬漫展摊位招募', summary: '12 月漫展社团摊位志愿者报名中。', date: '2026-11-02', pinned: false },
]

export const tags = ['全部', '日常', '活动', '节日', '校园', '治愈']

// 周课表 mock：某人的课表（weekday 0-6，lessonStart/End 1-12）
export const mySchedule: CourseSlot[] = [
  { name: '高等数学', location: '2-N130', weekday: 0, lessonStart: 1, lessonEnd: 2, weeks: [1, 2, 3, 4, 5] },
  { name: '大学英语', location: '1-305', weekday: 0, lessonStart: 5, lessonEnd: 6, weeks: [1, 2, 3] },
  { name: '数据结构', location: '3-201', weekday: 1, lessonStart: 3, lessonEnd: 4, weeks: [1, 2, 3, 4] },
  { name: '体育', location: '操场', weekday: 2, lessonStart: 1, lessonEnd: 2, weeks: [1, 2] },
  { name: '线性代数', location: '2-N110', weekday: 3, lessonStart: 7, lessonEnd: 8, weeks: [1, 2, 3, 4, 5] },
  { name: '程序设计', location: '3-405', weekday: 4, lessonStart: 5, lessonEnd: 6, weeks: [1, 2, 3] },
]

export const theirSchedule: CourseSlot[] = [
  { name: '大学物理', location: '2-N130', weekday: 0, lessonStart: 1, lessonEnd: 2, weeks: [1, 2, 3, 4, 5] },
  { name: '马原', location: '1-101', weekday: 0, lessonStart: 5, lessonEnd: 6, weeks: [1, 2, 3, 4] },
  { name: '英语听力', location: '2-205', weekday: 2, lessonStart: 1, lessonEnd: 2, weeks: [2, 3] },
  { name: '数据库概论', location: '3-201', weekday: 1, lessonStart: 3, lessonEnd: 4, weeks: [1, 2, 3, 4] },
]