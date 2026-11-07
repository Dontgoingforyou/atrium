export type PortalTimeEntry = {
  id: string
  user_sub: string
  task_id: string | null
  task_name: string | null
  worked_on: string
  minutes: number
  note: string | null
  is_tour_demo?: boolean
  /** Версия для CAS (optimistic locking). */
  version: number
  created_at: string
  updated_at: string
}

export type TimeEntryCreate = {
  worked_on: string
  minutes: number
  task_id?: string | null
  task_name?: string | null
  note?: string | null
  is_tour_demo?: boolean
}

export type TimeEntryBulkCreate = {
  date_from: string
  date_to: string
  weekdays?: number[]
  minutes: number
  task_id?: string | null
  task_name?: string | null
  note?: string | null
}

export type TimeEntryPatch = {
  expected_version: number
  worked_on?: string
  minutes?: number
  task_id?: string | null
  task_name?: string | null
  note?: string | null
}

export type TimeEntrySummary = {
  total_minutes: number
  entries_count: number
}

export type TimeEntryReportBucket = {
  period_label: string
  date_start: string
  date_end: string
  total_minutes: number
  entries_count: number
}

export type PortalSpecialistMonthlySummary = {
  user_sub: string
  full_name: string | null
  email: string | null
  total_minutes: number
  entries_count: number
  month: string
}

export type PagedResponse<T> = {
  items: T[]
  total: number
  skip: number
  limit: number
}

export type TimeEntryImportRowError = {
  row: number
  message: string
}

export type TimeEntryImportResult = {
  created: PortalTimeEntry[]
  created_count: number
  skipped_count: number
  errors: TimeEntryImportRowError[]
}
