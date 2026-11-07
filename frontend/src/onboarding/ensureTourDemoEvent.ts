import { createEvent, deleteEvent, listCalendars, searchEvents } from '../api/calendar/calendarApi'
import type { PortalCalendar } from '../types/calendar'
import { warnTourCleanupError } from './tourCleanupLog'

/** Отображаемый заголовок учебного события (поиск/reuse в туре). */
export const TOUR_DEMO_EVENT_TITLE = 'Учебное событие'

export const TOUR_DEMO_EVENT_DESCRIPTION =
  'Это учебное событие для онбординга. После обучения оно будет удалено.'

export type EnsureTourDemoEventResult =
  | { ok: true; created: boolean; eventId: string }
  | { ok: false; reason: string }

function pickOwnCalendarId(calendars: PortalCalendar[]): string {
  const owned = calendars.filter((c) => c.my_role === 'owner')
  return owned.find((c) => c.is_primary)?.id ?? owned[0]?.id ?? ''
}
/** Сегодня 10:00–11:00 локального времени в ISO UTC. */
export function buildTourDemoEventWindow(now = new Date()): { startsAt: string; endsAt: string } {
  const start = new Date(now)
  start.setHours(10, 0, 0, 0)
  const end = new Date(start)
  end.setHours(11, 0, 0, 0)
  return { startsAt: start.toISOString(), endsAt: end.toISOString() }
}

export async function ensureGuidedTourDemoEvent(
  currentUserSub: string,
): Promise<EnsureTourDemoEventResult> {
  if (!currentUserSub) {
    return {
      ok: false,
      reason: 'Не удалось подготовить учебное событие: пользователь не определён.',
    }
  }

  const found = await searchEvents({ q: TOUR_DEMO_EVENT_TITLE, limit: 20 })
  const existing = found.items.find((e) => e.title === TOUR_DEMO_EVENT_TITLE)
  if (existing) {
    return { ok: true, created: false, eventId: existing.id }
  }

  const calendars = await listCalendars()
  const calendarId = pickOwnCalendarId(calendars)
  if (!calendarId) {
    return {
      ok: false,
      reason: 'Не удалось подготовить учебное событие: нет собственного календаря.',
    }
  }

  const { startsAt, endsAt } = buildTourDemoEventWindow()
  const created = await createEvent({
    calendar_id: calendarId,
    title: TOUR_DEMO_EVENT_TITLE,
    description: TOUR_DEMO_EVENT_DESCRIPTION,
    starts_at: startsAt,
    ends_at: endsAt,
    attendees: [{ user_sub: currentUserSub }],
  })

  return { ok: true, created: true, eventId: created.id }
}

/** Удаляет учебное событие; 404 не блокирует завершение тура. */
export async function cleanupGuidedTourDemoEvent(eventId: string): Promise<void> {
  try {
    await deleteEvent(eventId)
  } catch (e) {
    warnTourCleanupError('demo event', e)
  }
}

export function calendarTourEventHref(eventId: string, edit: boolean): string {
  const base = `/calendar?event=${encodeURIComponent(eventId)}`
  return edit ? `${base}&edit=1` : base
}

/** Совпадение URL тура для карточки / формы редактирования события. */
export function calendarTourEventLocationMatches(
  pathname: string,
  search: string,
  eventId: string,
  edit: boolean,
): boolean {
  if (pathname !== '/calendar') return false
  const have = new URLSearchParams(search.startsWith('?') ? search.slice(1) : search)
  if (have.get('event') !== eventId) return false
  const hasEdit = have.get('edit') === '1'
  return edit ? hasEdit : !hasEdit
}

export { stepNeedsTourDemoEvent } from '../domain/onboarding/guidedTour'
