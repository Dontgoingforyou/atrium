import { describe, expect, it } from 'vitest'

import { eventToOccurrence } from '../../../src/domain/calendar/calendarEventToOccurrence'
import { DEFAULT_CALENDAR_COLOR } from '../../../src/domain/calendar/calendarColor'
import type { PortalCalendar, PortalCalendarEvent } from '../../../src/types/calendar'

function makeEvent(over: Partial<PortalCalendarEvent> = {}): PortalCalendarEvent {
  return {
    id: 'ev-1',
    calendar_id: 'cal-1',
    organizer_sub: 'sub-1',
    title: 'Дейлик',
    description: null,
    location: null,
    starts_at: '2026-08-26T07:00:00.000Z',
    ends_at: '2026-08-26T08:00:00.000Z',
    timezone: 'UTC',
    rrule: null,
    color: null,
    version: 1,
    created_at: '2026-08-26T00:00:00.000Z',
    updated_at: '2026-08-26T00:00:00.000Z',
    attendees: [],
    reminders: [],
    ...over,
  }
}

describe('eventToOccurrence', () => {
  it('мапит поля события в occurrence', () => {
    const ev = makeEvent({ title: 'Встреча', color: '#ff0000' })
    const occ = eventToOccurrence(ev, [])
    expect(occ.event_id).toBe('ev-1')
    expect(occ.calendar_id).toBe('cal-1')
    expect(occ.title).toBe('Встреча')
    expect(occ.color).toBe('#ff0000')
    expect(occ.original_start).toBe(ev.starts_at)
    expect(occ.starts_at).toBe(ev.starts_at)
    expect(occ.ends_at).toBe(ev.ends_at)
    expect(occ.is_cancelled).toBe(false)
    expect(occ.is_peer_view).toBe(false)
    expect(occ.attendees).toEqual([])
    expect(occ.reminders).toEqual([])
  })

  it('берёт цвет календаря, если у события color = null', () => {
    const ev = makeEvent({ color: null })
    const calendars: PortalCalendar[] = [
      { id: 'cal-1', owner_sub: 'sub-1', title: 'Мой', color: '#00aa00', timezone: 'UTC', is_primary: true, show_to_other_departments: false, my_role: 'owner', created_at: '', updated_at: '', members: [] },
    ]
    expect(eventToOccurrence(ev, calendars).calendar_color).toBe('#00aa00')
  })

  it('падает на дефолтный цвет, если календарь не найден', () => {
    const ev = makeEvent({ color: null })
    expect(eventToOccurrence(ev, []).calendar_color).toBe(DEFAULT_CALENDAR_COLOR)
  })

  it('передаёт rrule и organizer_sub', () => {
    const ev = makeEvent({ rrule: 'FREQ=WEEKLY', organizer_sub: 'sub-7' })
    const occ = eventToOccurrence(ev, [])
    expect(occ.rrule).toBe('FREQ=WEEKLY')
    expect(occ.organizer_sub).toBe('sub-7')
  })
})
