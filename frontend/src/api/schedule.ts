/** 课表 API：上传意图/完成、我的课表、公开课表、对比、可见性。 */
import { request } from './client'
import type {
  ScheduleCompareResult,
  ScheduleRecord,
  ScheduleSlot,
  ScheduleUploadIntent,
} from '@/types'

export function getMySchedules() {
  return request<{ items: ScheduleRecord[] }>({ method: 'GET', url: '/schedule/mine' })
}

export function createScheduleUploadIntent(filename: string, sizeBytes: number) {
  return request<ScheduleUploadIntent>({
    method: 'POST',
    url: '/schedule/upload-intent',
    data: { filename, size_bytes: sizeBytes },
  })
}

export function completeScheduleUpload(
  intent: ScheduleUploadIntent,
  originalName: string,
) {
  return request<ScheduleRecord>({
    method: 'POST',
    url: '/schedule/upload-complete',
    data: {
      bucket: intent.bucket,
      object_key: intent.object_key,
      original_name: originalName,
    },
  })
}

export function getSharedSchedule(username: string) {
  return request<ScheduleRecord>({
    method: 'GET',
    url: `/schedule/shared/${encodeURIComponent(username)}`,
  })
}

export function compareSchedules(slotsA: ScheduleSlot[], slotsB: ScheduleSlot[]) {
  return request<ScheduleCompareResult>({
    method: 'POST',
    url: '/schedule/compare',
    data: { slots_a: slotsA, slots_b: slotsB },
  })
}

export function setScheduleVisibility(scheduleId: string, isPublic: boolean) {
  return request<ScheduleRecord>({
    method: 'PATCH',
    url: `/schedule/${scheduleId}/visibility`,
    data: { is_public: isPublic },
  })
}

export function deleteSchedule(scheduleId: string) {
  return request<{ message: string }>({
    method: 'DELETE',
    url: `/schedule/${scheduleId}`,
  })
}
