export type CalendarMemberRole = 'owner' | 'editor' | 'viewer'

export type SharedDepartmentCalendar = {
  id: string
  owner_sub: string
  owner_label: string | null
  title: string
  department_id: string | null
  department_label: string
  show_to_other_departments: boolean
}

export type PortalCalendar = {
  id: string
  owner_sub: string
  /** Имя/почта владельца с BFF (есть и у test.*, которых нет в справочнике). */
  owner_label?: string | null
  title: string
  color: string
  timezone: string
  is_primary: boolean
  show_to_other_departments: boolean
  my_role: CalendarMemberRole | string
  created_at: string
  updated_at: string
  members: PortalCalendarMember[]
}

export type PortalCalendarMember = {
  id: string
  user_sub: string | null
  email: string | null
  role: string
  created_at: string
}

export type PortalCalendarAttendee = {
  id: string
  user_sub: string | null
  email: string
  status: string
  responded_at: string | null
  created_at: string
}

export type PortalCalendarReminder = {
  id: string
  offset_minutes: number
  channel: string
}

export type PortalCalendarOccurrence = {
  event_id: string
  calendar_id: string
  calendar_color: string
  color?: string | null
  original_start: string
  starts_at: string
  ends_at: string | null
  title: string
  description: string | null
  location: string | null
  timezone: string
  rrule: string | null
  organizer_sub: string
  is_cancelled: boolean
  is_peer_view?: boolean
  attendees: PortalCalendarAttendee[]
  reminders: PortalCalendarReminder[]
}

export type PortalCalendarEvent = {
  id: string
  calendar_id: string
  organizer_sub: string
  title: string
  description: string | null
  location: string | null
  starts_at: string
  ends_at: string | null
  timezone: string
  rrule: string | null
  color?: string | null
  /** Версия для CAS (optimistic locking). */
  version: number
  created_at: string
  updated_at: string
  attendees: PortalCalendarAttendee[]
  reminders: PortalCalendarReminder[]
}

export type CalendarEventSearchHit = {
  id: string
  calendar_id: string
  title: string
  starts_at: string
  ends_at: string | null
  calendar_title: string
  location: string | null
}

// --- Write-DTO (create/update) ---

export type CalendarAttendeeCreate = {
  user_sub: string
}

export type CalendarReminderCreate = {
  offset_minutes: number
  channel?: string
}

export type CalendarCreate = {
  title: string
  color?: string
  timezone?: string
}

export type CalendarUpdate = {
  title?: string
  color?: string
  timezone?: string
}

export type CalendarEventCreate = {
  calendar_id: string
  title: string
  description?: string | null
  location?: string | null
  starts_at: string
  ends_at?: string | null
  timezone?: string
  rrule?: string | null
  color?: string | null
  attendees?: CalendarAttendeeCreate[]
  reminders?: CalendarReminderCreate[]
}

export type CalendarOccurrenceOverride = {
  original_start: string
  starts_at?: string | null
  ends_at?: string | null
  title?: string | null
  description?: string | null
  location?: string | null
  is_cancelled?: boolean
}

export type CalendarEventPatch = {
  expected_version: number
  title?: string
  description?: string | null
  location?: string | null
  starts_at?: string
  ends_at?: string | null
  timezone?: string
  rrule?: string | null
  color?: string | null
  attendees?: CalendarAttendeeCreate[]
  reminders?: CalendarReminderCreate[]
}
