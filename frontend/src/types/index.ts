export interface ApiResponse<T> {
  success: boolean
  data: T | null
  error: { code: string; message: string } | null
  request_id: string | null
}

export interface Page<T> {
  items: T[]
  pagination: { page: number; page_size: number; total: number }
}

export type Role =
  | 'guest'
  | 'member'
  | 'photographer'
  | 'moderator'
  | 'admin'
  | 'super_admin'

export interface User {
  id: string
  username: string
  displayName: string
  role: Role
  avatar: string
  bio: string
}

// 后端 /auth/me 返回的原始结构（snake_case）
export interface MeResponse {
  id: string
  username: string
  display_name: string
  email: string
  bio: string
  avatar_url: string | null
  role: string
  status: string
  applied_role: string | null
  application_reason: string | null
  application_portfolio: string | null
  created_at: string
}

// 管理端用户（/admin/users 返回，snake_case）
export interface AdminUser {
  id: string
  username: string
  display_name: string
  email: string
  role: string
  status: string
  applied_role: string | null
  application_reason: string | null
  application_portfolio: string | null
  created_at: string
}

export interface GalleryImage {
  id: string
  url: string | null
  display_url: string | null
  thumb_url: string | null
  object_key: string | null
  original_name: string | null
  title: string
  description: string | null
  tags: string[]
  photographer: string
  photographer_avatar: string | null
  moderation_status: string
  is_public: boolean
  width: number | null
  height: number | null
  uploaded_at: string | null
  processing_status: string | null
}

// 后端 /images/upload-intent 返回
export interface UploadIntent {
  storage_provider: string
  bucket: string
  object_key: string
  visibility: string
  upload_url: string
  expires_in: number
}

// 私有相册图片（/profile/me/images 返回）
export interface ProfileImage {
  id: string
  original_name: string | null
  title: string | null
  description: string | null
  width: number | null
  height: number | null
  created_at: string | null
  processing_status: string | null
  thumb_url: string | null
}

export interface CourseSlot {
  name: string
  location: string
  weekday: number // 0=周一 … 6=周日
  lessonStart: number
  lessonEnd: number
  weeks: number[]
  campus?: string
}

// ---------- 课表（真实 API 返回，snake_case） ----------
export interface ScheduleSlot {
  kind?: 'course' | 'event' // 未标记的历史条目视为课程
  name: string
  location: string
  weekday: number // 0=周一 … 6=周日
  lesson_start: number
  lesson_end: number
  weeks: number[]
  campus: string | null
}

export interface ScheduleRecord {
  id: string
  revision: number
  original_name: string | null
  format: string | null
  slots: ScheduleSlot[]
  timing: ScheduleTiming
  is_public: boolean
  is_archived: boolean
  created_at: string | null
  expires_at: string | null
  owner?: { id: string; username: string; display_name: string }
}

export interface ScheduleSegments {
  noon: string
  afternoon: string
  evening: string
}

export interface ScheduleTiming {
  term_start: string | null
  first_start: string
  lesson_minutes: number
  break_minutes: number
  segments: ScheduleSegments
  periods: [string, string][]
}

export type ScheduleGroupJoinMode = 'open' | 'approval'
export type ScheduleGroupStatus = 'active' | 'pending'

export interface ScheduleGroupMine {
  role: 'owner' | 'member'
  status: ScheduleGroupStatus
  schedule_id: string | null
  can_manage: boolean
}

export interface ScheduleGroupSummary {
  id: string
  name: string
  code: string | null
  owner_id: string
  join_mode: ScheduleGroupJoinMode
  member_count: number
  pending_count: number
  my: ScheduleGroupMine
}

export interface ScheduleGroupStats {
  lesson_count: number
  both_free: number
  both_busy: number
  my_busy_only: number
  their_busy_only: number
  same_classroom: number
}

export interface ScheduleGroupMember {
  user_id: string
  username: string
  display_name: string
  role: 'owner' | 'member'
  is_me: boolean
  schedule_id: string | null
  schedule_name: string | null
  course_count: number
  slots: ScheduleSlot[]
  timing: ScheduleTiming | null
  stats: ScheduleGroupStats | null
}

export interface ScheduleGroupPending {
  user_id: string
  username: string
  display_name: string
  created_at: string | null
}

export interface ScheduleGroupDetail extends ScheduleGroupSummary {
  week: number | null
  members: ScheduleGroupMember[]
  pending: ScheduleGroupPending[]
}

export interface MealWindow {
  date_from: string
  date_to: string
  daily_start: string
  daily_end: string
  duration_minutes: number
  buffer_minutes: number
}
export interface MealInvite {
  schedule_id: string
  invitee_username: string
  title: string
  location?: string
  window: MealWindow
}
export interface FixedMeetupInvite {
  schedule_id: string
  invitee_username: string
  title: string
  location?: string
  week: number
  weekday: number
  lesson_start: number
  lesson_end: number
}
export interface CalendarEntry {
  id: string
  title: string
  location: string | null
  starts_at: string
  ends_at: string
  appointment_id: string | null
}
export interface AppointmentCandidate {
  id: string
  starts_at: string
  ends_at: string
}
export interface AppointmentDetail {
  id: string
  title: string
  location: string | null
  mode: 'meal' | 'fixed'
  fixed: {
    starts_at: string
    ends_at: string
    week: number | null
    weekday: number | null
    lesson_start: number | null
    lesson_end: number | null
  } | null
  window: MealWindow
  notice: string | null
  status: 'pending' | 'choosing' | 'confirming' | 'confirmed' | 'declined' | 'cancelled' | 'expired'
  candidates: AppointmentCandidate[]
  common_candidate_ids: string[]
  selected_candidate_id: string | null
  expires_at: string
  viewer_participant: {
    role: 'organizer' | 'invitee'
    status: 'invited' | 'accepted' | 'declined'
    choices: string[]
    confirmed_candidate_id: string | null
  }
  participants: {username: string; role: 'organizer' | 'invitee'; has_chosen: boolean; confirmed_candidate_id: string | null}[]
}

export interface ScheduleUploadIntent {
  storage_provider: string
  bucket: string
  object_key: string
  upload_url: string
  expires_in: number
}

export interface CompareFreeSlot {
  weekday: number
  lesson_start: number
  lesson_end: number
}

export interface CompareConflict {
  weekday: number
  a: ScheduleSlot
  b: ScheduleSlot
}

export interface ScheduleCompareResult {
  week: number | null
  same_classroom: CompareConflict[]
  both_free: CompareFreeSlot[]
  overlaps: CompareConflict[]
}

// ---------- 站点配置 / 公告 ----------
export interface PublicConfig {
  site_name: string
  site_subtitle: string
  logo_url: string | null
  favicon_url: string | null
  icp_number: string | null
  police_number: string | null
  registration_config?: RegistrationConfig
  oauth_config?: OauthConfig
}

export interface RegistrationConfig {
  registration_enabled: boolean
  require_email_verification: boolean
  require_phone_verification: boolean
}

export interface OauthConfig {
  enabled: boolean
  qq_enabled: boolean
}

export interface OauthProviderInfo {
  id: string
  enabled: boolean
}

export interface OauthProvidedUser {
  id: string
  username: string
  display_name: string
  role: string
  avatar_url: string | null
  bio: string
}

export interface OauthResolveResult {
  bound: boolean
  user?: OauthProvidedUser
  oauth_token?: string
  provider?: string
  nickname?: string
  return_to?: string
  access_token?: string
  token_type?: string
  expires_in?: number
  refresh_token?: string
}

export interface ThirdPartyBinding {
  provider: string
  provider_user_id: string
  created_at: string | null
}

export interface FooterLink {
  label: string
  href: string
}

export interface FooterConfig {
  links: FooterLink[]
  icp_number: string | null
  police_number: string | null
  copyright_owner: string
}

export interface LegalConfig {
  terms_url: string | null
  privacy_url: string | null
  copyright_notice: string | null
  contact_email: string | null
}

export interface ClubIntro {
  title: string
  content: string
}

export interface AnnouncementRecord {
  id: string
  title: string
  content: string
  status: string // draft / published / expired
  is_pinned: boolean
  published_at: string | null
  expires_at: string | null
  created_at: string | null
  updated_at: string | null
}

export interface SiteSettingRecord {
  key: string
  value: Record<string, unknown>
  category: string | null
  is_public: boolean
  updated_at: string | null
}

// ---------- 活动 ----------
export interface EventRecord {
  id: string
  title: string
  description: string | null
  location: string | null
  starts_at: string | null
  ends_at: string | null
  capacity: number | null
  registration_starts_at: string | null
  registration_ends_at: string | null
  status: string // draft / published / cancelled
  created_by: string | null
  registered_count: number
  waitlist_count: number
  my_status?: string | null // registered / waitlisted / checked_in / null
  my_registration?: EventRegistration | null
}

export interface EventRegistration {
  id: string
  event_id: string
  user_id: string
  status: string // registered / waitlisted / cancelled / checked_in
  signup_at: string | null
  checkin_at: string | null
  user?: {
    id: string
    username: string
    display_name: string
  }
}

// ---------- 动态页面 ----------
export interface PageBlock {
  type: string
  props: Record<string, unknown>
}

export interface PageSchema {
  slug?: string
  title?: string
  theme?: { primary?: string; background?: string }
  blocks: PageBlock[]
}

export interface PageRecord {
  id: string
  slug: string
  title: string
  status: string // draft / published / archived
  schema_json: PageSchema | Record<string, unknown>
  starts_at: string | null
  ends_at: string | null
  seo_title: string | null
  seo_description: string | null
  published_at: string | null
  created_at: string | null
  updated_at: string | null
}

export interface PageVersion {
  id: string
  page_id: string
  version: number
  schema_snapshot: PageSchema | Record<string, unknown>
  change_summary: string | null
  created_at: string | null
}

// ---------- 图片管理 ----------
export interface AdminImageStats {
  total: number
  pending: number
  approved: number
  rejected: number
}

// 公开成员信息
export interface MemberProfile {
  id: string
  username: string
  display_name: string
  role: string
  bio: string
  avatar_url: string | null
}

// ---------- 个人主页客制化 ----------
// 契约见 docs；props 用 Record<string, unknown> 承载，渲染时按类型窄化
export type ProfileBlockType =
  | 'bio'
  | 'quote'
  | 'featured_photo'
  | 'photo_wall'
  | 'gallery_link'
  | 'links'
  | 'stats'
  | 'html_block'

// 12 栅格制：移动端一律塌成 12
export type ProfileSpan = 3 | 4 | 6 | 8 | 12

export interface ProfileBlock {
  id: string
  type: ProfileBlockType
  span: ProfileSpan
  props: Record<string, unknown>
}

export interface ProfileLinkItem {
  label: string
  url: string
}

export type ProfileStatsKey = 'joined_days' | 'gallery_image_count'

export interface ProfileStats {
  joined_days: number
  gallery_image_count: number
}

// 服务端解析好的图片地址；键为 object_key
export interface ProfileMedia {
  thumb_url: string | null
  display_url: string | null
  width: number | null
  height: number | null
}

export type ProfileBackgroundType = 'solid' | 'gradient' | 'image'
export type ProfileCardStyle = 'glass' | 'solid' | 'outline'

export interface ProfileTheme {
  primary: string
  accent: string
  background_type: ProfileBackgroundType
  background_key: string | null
  background_blur: number
  card_style: ProfileCardStyle
}

export interface ProfilePageUser {
  username: string
  display_name: string
  avatar_url: string | null
}

export interface ProfilePageResponse {
  user: ProfilePageUser
  theme: ProfileTheme
  blocks: ProfileBlock[]
  media: Record<string, ProfileMedia>
  media_expires_in: number
  stats: ProfileStats
  published_at: string | null
}

export interface ProfileLayoutResponse {
  theme: ProfileTheme
  draft_blocks: ProfileBlock[]
  published_blocks: ProfileBlock[] | null
  is_public: boolean
  max_blocks: number
  media: Record<string, ProfileMedia>
  media_expires_in: number
  stats: ProfileStats
}

// 本人可引用的私有图片（仅 is_displayable 的会出现在公开页）
export interface ProfileMediaOption {
  id: string
  object_key: string
  title: string | null
  created_at: string | null
  is_displayable: boolean
  thumb_url: string | null
  display_url: string | null
  width: number | null
  height: number | null
}
