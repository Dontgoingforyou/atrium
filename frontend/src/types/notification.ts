export type PortalNotification = {
  id: string
  recipient_sub: string
  type: string
  task_id: string | null
  comment_id: string | null
  document_id: string | null
  document_comment_id: string | null
  calendar_event_id?: string | null
  calendar_id?: string | null
  author_sub: string
  created_at: string
  read_at: string | null
  // Обогащённые поля (заполняются бэкендом при листинге)
  task_title: string | null
  task_priority: string | null
  task_due_at: string | null
  task_status: string | null
  document_title: string | null
  calendar_event_title?: string | null
  calendar_event_starts_at?: string | null
  calendar_event_location?: string | null
  calendar_event_timezone?: string | null
  calendar_title?: string | null
  context_title?: string | null
  author_display_name: string | null
  author_avatar_url?: string | null
}

export type NotificationUnreadCount = {
  unread_count: number
}
