import type {
  PortalCalendar,
  PortalCalendarEvent,
  PortalCalendarOccurrence,
} from '../../types/calendar'
import { DEFAULT_CALENDAR_COLOR } from './calendarColor'

/** Маппинг единичного события в occurrence для отображения в сетке (без повторов). */
export function eventToOccurrence(
  ev: PortalCalendarEvent,
  calendars: PortalCalendar[],
): PortalCalendarOccurrence {
  const cal = calendars.find((c) => c.id === ev.calendar_id)
  return {
    event_id: ev.id,
    calendar_id: ev.calendar_id,
    calendar_color: cal?.color ?? DEFAULT_CALENDAR_COLOR,
    color: ev.color ?? null,
    original_start: ev.starts_at,
    starts_at: ev.starts_at,
    ends_at: ev.ends_at,
    title: ev.title,
    description: ev.description,
    location: ev.location,
    timezone: ev.timezone,
    rrule: ev.rrule,
    organizer_sub: ev.organizer_sub,
    is_cancelled: false,
    is_peer_view: false,
    attendees: ev.attendees,
    reminders: ev.reminders,
  }
}
