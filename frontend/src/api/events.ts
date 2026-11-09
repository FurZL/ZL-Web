/** 活动 API：公开列表/详情/报名/取消/签到 + 管理 CRUD */
import { request } from './client'
import type { EventRecord, EventRegistration } from '@/types'

// ---------- 公开 / 成员 ----------

export function listEvents() {
  return request<{ items: EventRecord[] }>({ method: 'GET', url: '/events/' })
}

export function getEvent(eventId: string) {
  return request<EventRecord>({ method: 'GET', url: `/events/${eventId}` })
}

export function registerEvent(eventId: string, idempotencyKey?: string) {
  return request<EventRegistration>({
    method: 'POST',
    url: `/events/${eventId}/register`,
    data: { idempotency_key: idempotencyKey ?? null },
  })
}

export function cancelEventRegistration(eventId: string) {
  return request<{ message: string }>({
    method: 'DELETE',
    url: `/events/${eventId}/register`,
  })
}

export function eventCheckin(eventId: string) {
  return request<EventRegistration>({
    method: 'POST',
    url: `/events/${eventId}/checkin`,
  })
}

// ---------- 管理端 ----------

export function adminListEvents() {
  return request<{ items: EventRecord[] }>({ method: 'GET', url: '/admin/events/' })
}

export function adminCreateEvent(data: {
  title: string
  description?: string | null
  location?: string | null
  starts_at: string
  ends_at: string
  capacity?: number | null
  registration_starts_at?: string | null
  registration_ends_at?: string | null
  publish_now?: boolean
}) {
  return request<EventRecord>({ method: 'POST', url: '/admin/events/', data })
}

export function adminGetEventDetail(eventId: string) {
  return request<{
    event: EventRecord
    items: EventRegistration[]
    registered_count: number
    waitlist_count: number
  }>({ method: 'GET', url: `/admin/events/${eventId}` })
}

export function adminUpdateEvent(
  eventId: string,
  data: {
    title?: string
    description?: string | null
    location?: string | null
    starts_at?: string
    ends_at?: string
    capacity?: number | null
    registration_starts_at?: string | null
    registration_ends_at?: string | null
  },
) {
  return request<EventRecord>({ method: 'PATCH', url: `/admin/events/${eventId}`, data })
}

export function adminSetEventStatus(eventId: string, status: string) {
  return request<EventRecord>({
    method: 'PATCH',
    url: `/admin/events/${eventId}/status`,
    data: { status },
  })
}

export function adminDeleteEvent(eventId: string) {
  return request<{ message: string }>({
    method: 'DELETE',
    url: `/admin/events/${eventId}`,
  })
}

export function adminListRegistrations(eventId: string) {
  return request<{
    event: EventRecord
    items: EventRegistration[]
    registered_count: number
    waitlist_count: number
  }>({ method: 'GET', url: `/admin/events/${eventId}/registrations` })
}

export function adminCheckin(eventId: string, registrationId: string) {
  return request<EventRegistration>({
    method: 'POST',
    url: `/admin/events/${eventId}/registrations/${registrationId}/checkin`,
  })
}
