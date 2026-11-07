import type { PortalFavorite } from './favorite'
import type { PortalTask } from './task'
import type { TimeEntryReportBucket, TimeEntrySummary } from './timeEntry'

export type TaskOpenByPriority = {
  low: number
  medium: number
  high: number
}

export type TaskByStatus = {
  todo: number
  in_progress: number
}

export type TeamAssigneeLoad = {
  assignee_sub: string
  open_count: number
  overdue_count: number
  display_name: string | null
  avatar_url?: string | null
  avatar_focal_x?: number | null
  avatar_focal_y?: number | null
}

export type HomeAdminBlock = {
  team_open_count: number
  team_overdue_count: number
  team_tasks_preview: PortalTask[]
  team_open_by_priority: TaskOpenByPriority
  team_done_this_month: number
  team_no_assignee_count: number
  team_by_status: TaskByStatus
  team_assignee_load: TeamAssigneeLoad[]
}

export type HomeManagerBlock = {
  section_open_count: number
  section_overdue_count: number
  section_tasks_preview: PortalTask[]
  section_open_by_priority: TaskOpenByPriority
  section_done_this_month: number
  section_no_assignee_count: number
  section_by_status: TaskByStatus
  timesheet_current_month: TimeEntrySummary
  timesheet_weekly_buckets: TimeEntryReportBucket[]
}

export type AssigneeHomeDrilldown = {
  assignee_sub: string
  display_name: string | null
  avatar_url?: string | null
  avatar_focal_x?: number | null
  avatar_focal_y?: number | null
  open_count: number
  overdue_count: number
  open_tasks_preview: PortalTask[]
  overdue_tasks_preview: PortalTask[]
  open_by_priority: TaskOpenByPriority
}

export type HomeData = {
  my_tasks_preview: PortalTask[]
  my_tasks_open_count: number
  my_tasks_overdue_count: number
  favorites_preview: PortalFavorite[]
  search: { get_path: string }
  admin: HomeAdminBlock | null
  manager: HomeManagerBlock | null
  assignee_drilldown: AssigneeHomeDrilldown | null
}
