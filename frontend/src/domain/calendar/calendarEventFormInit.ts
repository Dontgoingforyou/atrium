import type { PortalCalendarOccurrence } from '../../types/calendar'
import { DEFAULT_REMINDER_OFFSET_MINUTES } from './calendarReminderPresets'

/** Начальный список sub'ов участников в форме события. */
export function initialGuestSubs(
  mode: 'create' | 'edit',
  currentSub: string | undefined,
  occurrence: PortalCalendarOccurrence | null,
  peerCreateForSub?: string | null,
): string[] {
  if (mode === 'edit' && occurrence) {
    const fromOcc = occurrence.attendees
      .map((a) => a.user_sub)
      .filter((s): s is string => Boolean(s))
    if (fromOcc.length) return fromOcc
    return currentSub ? [currentSub] : []
  }
  if (peerCreateForSub) return [peerCreateForSub]
  return currentSub ? [currentSub] : []
}

/** Начальный список offset'ов напоминаний в форме события. */
export function initialReminderOffsets(occurrence: PortalCalendarOccurrence | null): number[] {
  if (occurrence?.reminders.length) {
    return occurrence.reminders.map((r) => r.offset_minutes)
  }
  return [DEFAULT_REMINDER_OFFSET_MINUTES]
}
