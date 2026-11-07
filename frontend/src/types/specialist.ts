import type { RichMediaRead } from './richMedia'

/** Типы для доски воронки специалистов. */

export type SpecialistColumn = {
  id: string
  key: string
  title: string
  color: string
  position: number
}

export type SpecialistBoardPref = {
  column_order: string[]
  hidden_column_keys: string[]
}

export type SpecialistBoardPrefWrite = {
  column_order: string[]
  hidden_column_keys: string[]
}

export type SpecialistStatus = {
  id: string
  title: string
  color: string
}

export type ManagerSpecialistEntry = {
  id: string
  specialist_sub: string
  display_name: string | null
  email: string | null
  avatar_url: string | null
  column_key: string
  position: number
  version: number
  manager_sub: string
  manager_display_name: string | null
  status_id: string | null
  status_title: string | null
  status_color: string | null
  created_at: string
}

export type ManagerSpecialistAdd = {
  specialist_sub: string
  column_key?: string
}

export type ManagerSpecialistPatch = {
  expected_version: number
  column_key?: string
  position?: number
}

export type ManagerSpecialistReorder = {
  entry_id: string
  column_key: string
  after_entry_id: string | null
  before_entry_id: string | null
}

/** Менеджер, за которым закреплён специалист (для drawer-панели на /specialists). */
export type SpecialistManagerRef = {
  manager_sub: string
  manager_display_name: string | null
  manager_avatar_url?: string | null
  manager_avatar_focal_x?: number | null
  manager_avatar_focal_y?: number | null
  column_key: string
  status_id: string | null
  status_title: string | null
  status_color: string | null
  created_at: string
}

/** Расширенный профиль специалиста (персональные данные). */
export type SpecialistProfile = {
  specialist_sub: string
  full_name: string | null
  email: string | null
  username: string | null
  birthdate: string | null
  location: string | null
  telegram: string | null
  jira_issue_key?: string | null
  direction_title?: string | null
  /** Версия для CAS (optimistic locking). */
  version: number
}

/** Ссылка к профилю специалиста (CV, портфолио и т.д.). */
export type SpecialistLink = {
  id: string
  specialist_sub: string
  title: string
  url: string
  created_by_sub: string | null
  created_at: string
}

export type JiraSearchHit = {
  issue_key: string
  summary: string
  status_name: string
}

export type JiraFieldRead = {
  id: string
  label: string
  group: string
  value: string | null
  kind: string
}

export type JiraFieldGroupRead = {
  key: string
  label: string
  fields: JiraFieldRead[]
}

export type SpecialistJiraState = {
  specialist_sub: string
  jira_issue_key: string | null
  jira_browse_url: string | null
  jira_synced_at: string | null
  groups: JiraFieldGroupRead[]
}

/** Комментарий о специалисте. */
export type SpecialistNote = {
  id: string
  specialist_sub: string
  parent_id: string | null
  author_sub: string
  author_display_name: string | null
  body: string
  mentions: string[]
  version: number
  created_at: string
  updated_at: string
  replies: SpecialistNote[]
  media?: RichMediaRead[]
}

export type SpecialistProfilePatch = {
  expected_version: number
} & Partial<Pick<SpecialistProfile, 'birthdate' | 'location' | 'telegram'>>
