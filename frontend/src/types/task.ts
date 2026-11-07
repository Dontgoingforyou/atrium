import type { PortalTag } from './document'
import type { ThreadComment, ThreadCommentCreate, ThreadCommentUpdate } from './commentThread'

export type { PortalTag }

export type TaskStatus = 'todo' | 'in_progress' | 'done' | 'cancelled' | (string & {})
export type TaskPriority = 'low' | 'medium' | 'high'

export type PortalTask = {
  id: string
  number: number | null
  title: string
  description: string | null
  creator_sub: string
  assignee_sub: string | null
  assignee_subs: string[]
  status: string
  priority: TaskPriority
  due_at: string | null
  document_id: string | null
  document_title?: string | null
  chat_id: string | null
  source_message_id: string | null
  parent_task_id: string | null
  position: number
  jira_issue_key?: string | null
  jira_sync_error?: string | null
  /** Учебная задача онбординга; автор может удалить только с этим флагом. */
  is_tour_demo?: boolean
  /** Версия для CAS (optimistic locking). */
  version: number
  created_at: string
  updated_at: string
  tags: PortalTag[]
}

export type TaskCreate = {
  title: string
  description?: string | null
  status?: string
  priority?: TaskPriority
  assignee_sub?: string | null
  assignee_subs?: string[]
  document_id?: string | null
  /** ID сообщения чата, из которого создана задача (бэкенд принимает на create). */
  source_message_id?: string | null
  /** ID чата-источника задачи (бэкенд принимает на create). */
  chat_id?: string | null
  due_at?: string | null
  parent_task_id?: string | null
  tag_ids?: string[]
  is_tour_demo?: boolean
}

export type TaskPatch = {
  expected_version: number
  title?: string
  description?: string | null
  status?: string
  priority?: TaskPriority
  assignee_sub?: string | null
  assignee_subs?: string[]
  due_at?: string | null
  tag_ids?: string[] | null
  document_id?: string | null
  parent_task_id?: string | null
}

export type TaskHistoryEntry = {
  id: string
  task_id: string
  changed_at: string
  changed_by_sub: string
  diff: Record<string, { old: unknown; new: unknown }>
}

export type TaskComment = ThreadComment & {
  task_id: string
  replies: TaskComment[]
}

export type TaskCommentCreate = Pick<ThreadCommentCreate, 'body'> &
  Partial<Pick<ThreadCommentCreate, 'parent_id' | 'mentions' | 'media_ids'>>

/** Совпадает с ThreadCommentUpdate — alias для семантической колокации с задачами. */
export type TaskCommentUpdate = ThreadCommentUpdate

export type TaskReorder = {
  task_id: string
  status: string
  after_task_id: string | null
  before_task_id: string | null
}

export type PortalTaskColumn = {
  id: string
  title: string
  color: string
  status_key: string
  position: number
  exclude_from_kpi: boolean
  /** ID статуса Jira на доске AUTASKS (только portal_admin при обновлении). */
  jira_status_id?: string | null
}

export type TaskColumnCreate = {
  title: string
  color: string
  status_key: string
  position?: number
  exclude_from_kpi?: boolean
}

export type TaskColumnUpdate = {
  title?: string
  color?: string
  position?: number
  exclude_from_kpi?: boolean
  /** ID статуса Jira на доске AUTASKS; только portal_admin. */
  jira_status_id?: string | null
}

export type TaskBoardPref = {
  column_order: string[]
  hidden_status_keys: string[]
  title_overrides: Record<string, string>
  subtasks_flat?: boolean
  hide_subtasks?: boolean
}

export type TaskBoardPrefWrite = {
  column_order: string[]
  hidden_status_keys: string[]
  title_overrides: Record<string, string>
  subtasks_flat?: boolean
  hide_subtasks?: boolean
}

export type TaskLink = {
  id: string
  task_id: string
  title: string | null
  url: string
  created_by_sub: string
  created_at: string
}

export type TaskLinkCreate = {
  title?: string
  url: string
}

export type TaskFile = {
  id: string
  task_id: string
  original_filename: string
  content_type: string
  file_size: number
  download_url: string
  view_url: string
  uploaded_by_sub: string
  created_at: string
}
