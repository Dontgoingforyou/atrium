import type { PortalCalendar } from '../../types/calendar'

type OccurrenceEditInput = {
  organizer_sub: string
  is_peer_view?: boolean
  is_cancelled?: boolean
}

export function ownCalendars(calendars: PortalCalendar[]): PortalCalendar[] {
  return calendars.filter((c) => c.my_role === 'owner')
}

export function defaultOwnCalendarId(calendars: PortalCalendar[]): string {
  const owned = ownCalendars(calendars)
  return owned.find((c) => c.is_primary)?.id ?? owned[0]?.id ?? ''
}

export function canEditCalendarOccurrence(
  occurrence: OccurrenceEditInput | null | undefined,
  currentUserSub: string | null,
  calendarRole?: string | null,
): boolean {
  if (!occurrence || !currentUserSub) return false
  if (occurrence.organizer_sub === currentUserSub) return true
  if (occurrence.is_peer_view) return false
  return calendarRole === 'owner' || calendarRole === 'editor'
}

export function canDragCalendarOccurrence(
  occurrence: OccurrenceEditInput | null | undefined,
  currentUserSub: string | null,
  calendarRole?: string | null,
): boolean {
  if (!occurrence || occurrence.is_cancelled) return false
  return canEditCalendarOccurrence(occurrence, currentUserSub, calendarRole)
}
