import { parseJsonOrThrowApi } from '../parseResponse'
import { authenticatedFetch } from '../rawClient'
import type {
  CalendarCreate,
  CalendarEventCreate,
  CalendarEventPatch,
  CalendarOccurrenceOverride,
  CalendarEventSearchHit,
  CalendarUpdate,
  PortalCalendar,
  PortalCalendarAttendee,
  PortalCalendarEvent,
  PortalCalendarOccurrence,
  SharedDepartmentCalendar,
} from '../../types/calendar'
import type { PagedResponse } from '../../types/timeEntry'

const BASE = '/portal/calendar'

export async function getPeerCalendarContext(userSub: string): Promise<{
  calendar_id: string
  owner_sub: string
}> {
  const q = new URLSearchParams({ user_sub: userSub })
  const res = await authenticatedFetch(`${BASE}/calendars/peer-context?${q.toString()}`)
  return parseJsonOrThrowApi(res)
}

export async function listCalendars(): Promise<PortalCalendar[]> {
  const res = await authenticatedFetch(`${BASE}/calendars`)
  return parseJsonOrThrowApi(res)
}

export async function listSharedCalendars(): Promise<SharedDepartmentCalendar[]> {
  const res = await authenticatedFetch(`${BASE}/calendars/shared`)
  return parseJsonOrThrowApi(res)
}

export async function createCalendar(body: CalendarCreate): Promise<PortalCalendar> {
  const res = await authenticatedFetch(`${BASE}/calendars`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi(res)
}

export async function setCalendarShow(calendarId: string, enabled: boolean): Promise<PortalCalendar> {
  const res = await authenticatedFetch(`${BASE}/calendars/${calendarId}/show`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ enabled }),
  })
  return parseJsonOrThrowApi(res)
}

export async function updateCalendar(
  calendarId: string,
  body: CalendarUpdate,
): Promise<PortalCalendar> {
  const res = await authenticatedFetch(`${BASE}/calendars/${calendarId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi(res)
}

export async function deleteCalendar(calendarId: string): Promise<void> {
  const res = await authenticatedFetch(`${BASE}/calendars/${calendarId}`, {
    method: 'DELETE',
  })
  await parseJsonOrThrowApi(res)
}

export async function listOccurrences(params: {
  from: string
  to: string
  calendarIds?: string[]
  userSub?: string | null
}): Promise<PortalCalendarOccurrence[]> {
  const q = new URLSearchParams({ from: params.from, to: params.to })
  for (const id of params.calendarIds ?? []) {
    q.append('calendar_id', id)
  }
  if (params.userSub) {
    q.set('user_sub', params.userSub)
  }
  const res = await authenticatedFetch(`${BASE}/occurrences?${q.toString()}`)
  return parseJsonOrThrowApi(res)
}

export async function searchEvents(params: {
  q: string
  skip?: number
  limit?: number
}): Promise<PagedResponse<CalendarEventSearchHit>> {
  const q = new URLSearchParams({ q: params.q })
  if (params.skip != null) q.set('skip', String(params.skip))
  if (params.limit != null) q.set('limit', String(params.limit))
  const res = await authenticatedFetch(`${BASE}/events/search?${q.toString()}`)
  return parseJsonOrThrowApi(res)
}

export async function createEvent(body: CalendarEventCreate): Promise<PortalCalendarEvent> {
  const res = await authenticatedFetch(`${BASE}/events`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi(res)
}

function eventUrl(eventId: string, calendarId?: string, suffix = ''): string {
  const query = calendarId ? `?calendar_id=${encodeURIComponent(calendarId)}` : ''
  return `${BASE}/events/${eventId}${suffix}${query}`
}

export async function getEvent(eventId: string, calendarId?: string): Promise<PortalCalendarEvent> {
  const res = await authenticatedFetch(eventUrl(eventId, calendarId))
  return parseJsonOrThrowApi(res)
}

export async function updateEvent(
  eventId: string,
  body: CalendarEventPatch,
  calendarId?: string,
): Promise<PortalCalendarEvent> {
  const res = await authenticatedFetch(eventUrl(eventId, calendarId), {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi(res)
}

/** PATCH с CAS: если version не передана — читает текущую с сервера. */
export async function updateEventWithCas(
  eventId: string,
  patch: Omit<CalendarEventPatch, 'expected_version'>,
  expectedVersion?: number,
  calendarId?: string,
): Promise<PortalCalendarEvent> {
  const version = expectedVersion ?? (await getEvent(eventId, calendarId)).version
  return updateEvent(eventId, { ...patch, expected_version: version }, calendarId)
}

export async function overrideEventOccurrence(
  eventId: string,
  body: CalendarOccurrenceOverride,
  calendarId?: string,
): Promise<PortalCalendarEvent> {
  const res = await authenticatedFetch(eventUrl(eventId, calendarId, '/overrides'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi(res)
}

export async function deleteEvent(eventId: string, calendarId?: string): Promise<void> {
  const res = await authenticatedFetch(eventUrl(eventId, calendarId), { method: 'DELETE' })
  await parseJsonOrThrowApi(res)
}

export async function addEventAttendee(eventId: string, userSub: string): Promise<PortalCalendarAttendee> {
  const res = await authenticatedFetch(`${BASE}/events/${eventId}/attendees`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_sub: userSub }),
  })
  return parseJsonOrThrowApi(res)
}

export async function acceptCalendarInvite(token: string): Promise<{
  kind: string
  calendar_id: string | null
  event_id: string | null
  message: string
}> {
  const res = await authenticatedFetch(`${BASE}/invites/${encodeURIComponent(token)}/accept`, {
    method: 'POST',
  })
  return parseJsonOrThrowApi(res)
}
