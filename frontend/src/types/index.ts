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