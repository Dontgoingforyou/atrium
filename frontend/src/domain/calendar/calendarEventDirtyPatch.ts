import type { CalendarAttendeeCreate, CalendarEventPatch, CalendarReminderCreate } from '../../types/calendar'

export type CalendarEventFormSnapshot = {
  title: string
  description: string | null
  location: string | null
  starts_at: string
  ends_at: string | null
  rrule: string | null
  color: string | null
  attendees: CalendarAttendeeCreate[]
  reminders: CalendarReminderCreate[]
}

export type CalendarEventDirtyPatch = Omit<CalendarEventPatch, 'expected_version'>

function sameNullableText(a: string | null, b: string | null): boolean {
  return (a ?? null) === (b ?? null)
}

function attendeeSubs(items: CalendarAttendeeCreate[]): string[] {
  return [...new Set(items.map((a) => a.user_sub))].sort()
}

function reminderOffsets(items: CalendarReminderCreate[]): number[] {
  return [...new Set(items.map((r) => r.offset_minutes))].sort((x, y) => x - y)
}

function sameStringList(a: string[], b: string[]): boolean {
  return a.length === b.length && a.every((value, i) => value === b[i])
}

function sameNumberList(a: number[], b: number[]): boolean {
  return a.length === b.length && a.every((value, i) => value === b[i])
}

export function buildCalendarEventDirtyPatch(
  initial: CalendarEventFormSnapshot,
  current: CalendarEventFormSnapshot,
): CalendarEventDirtyPatch {
  const patch: CalendarEventDirtyPatch = {}
  if (initial.title !== current.title) patch.title = current.title
  if (!sameNullableText(initial.description, current.description)) {
    patch.description = current.description
  }
  if (!sameNullableText(initial.location, current.location)) {
    patch.location = current.location
  }
  if (initial.starts_at !== current.starts_at) patch.starts_at = current.starts_at
  if (!sameNullableText(initial.ends_at, current.ends_at)) patch.ends_at = current.ends_at
  if (!sameNullableText(initial.rrule, current.rrule)) patch.rrule = current.rrule
  if (!sameNullableText(initial.color, current.color)) patch.color = current.color
  if (!sameStringList(attendeeSubs(initial.attendees), attendeeSubs(current.attendees))) {
    patch.attendees = current.attendees
  }
  if (!sameNumberList(reminderOffsets(initial.reminders), reminderOffsets(current.reminders))) {
    patch.reminders = current.reminders
  }
  return patch
}

export function isCalendarEventDirtyPatchEmpty(patch: CalendarEventDirtyPatch): boolean {
  return Object.keys(patch).length === 0
}
