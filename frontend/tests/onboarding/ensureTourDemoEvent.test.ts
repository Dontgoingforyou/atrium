import { describe, expect, it, vi, beforeEach } from 'vitest'

import {
  buildTourDemoEventWindow,
  calendarTourEventHref,
  calendarTourEventLocationMatches,
  cleanupGuidedTourDemoEvent,
  ensureGuidedTourDemoEvent,
  stepNeedsTourDemoEvent,
  TOUR_DEMO_EVENT_DESCRIPTION,
  TOUR_DEMO_EVENT_TITLE,
} from '../../src/onboarding/ensureTourDemoEvent'

vi.mock('../../src/api/calendar/calendarApi', () => ({
  listCalendars: vi.fn(),
  searchEvents: vi.fn(),
  createEvent: vi.fn(),
  deleteEvent: vi.fn(),
}))

import { createEvent, deleteEvent, listCalendars, searchEvents } from '../../src/api/calendar/calendarApi'

describe('ensureGuidedTourDemoEvent', () => {
  beforeEach(() => {
    vi.mocked(listCalendars).mockReset()
    vi.mocked(searchEvents).mockReset()
    vi.mocked(createEvent).mockReset()
    vi.mocked(deleteEvent).mockReset()
  })

  it('reuses existing event with tour title', async () => {
    vi.mocked(searchEvents).mockResolvedValue({
      items: [{ id: 'ev1', title: TOUR_DEMO_EVENT_TITLE } as never],
      total: 1,
      skip: 0,
      limit: 20,
    })
    const result = await ensureGuidedTourDemoEvent('me')
    expect(result).toEqual({ ok: true, created: false, eventId: 'ev1' })
    expect(createEvent).not.toHaveBeenCalled()
  })

  it('creates event on primary calendar when missing', async () => {
    vi.mocked(searchEvents).mockResolvedValue({ items: [], total: 0, skip: 0, limit: 20 })
    vi.mocked(listCalendars).mockResolvedValue([
      {
        id: 'cal-primary',
        is_primary: true,
        my_role: 'owner',
        title: 'Основной',
      } as never,
    ])
    vi.mocked(createEvent).mockResolvedValue({ id: 'ev-new' } as never)

    const result = await ensureGuidedTourDemoEvent('me')
    expect(result).toEqual({ ok: true, created: true, eventId: 'ev-new' })
    expect(createEvent).toHaveBeenCalledWith(
      expect.objectContaining({
        calendar_id: 'cal-primary',
        title: TOUR_DEMO_EVENT_TITLE,
        description: TOUR_DEMO_EVENT_DESCRIPTION,
        attendees: [{ user_sub: 'me' }],
      }),
    )
  })

  it('fails without current user', async () => {
    const result = await ensureGuidedTourDemoEvent('')
    expect(result.ok).toBe(false)
    expect(createEvent).not.toHaveBeenCalled()
  })

  it('fails without own calendar', async () => {
    vi.mocked(searchEvents).mockResolvedValue({ items: [], total: 0, skip: 0, limit: 20 })
    vi.mocked(listCalendars).mockResolvedValue([])
    const result = await ensureGuidedTourDemoEvent('me')
    expect(result.ok).toBe(false)
  })

  it('не создаёт событие на чужом календаре (только editor)', async () => {
    vi.mocked(searchEvents).mockResolvedValue({ items: [], total: 0, skip: 0, limit: 20 })
    vi.mocked(listCalendars).mockResolvedValue([
      {
        id: 'cal-shared',
        is_primary: true,
        my_role: 'editor',
        title: 'Чужой',
      } as never,
    ])
    const result = await ensureGuidedTourDemoEvent('me')
    expect(result.ok).toBe(false)
    expect(createEvent).not.toHaveBeenCalled()
  })

  it('attendees — только текущий user', async () => {
    vi.mocked(searchEvents).mockResolvedValue({ items: [], total: 0, skip: 0, limit: 20 })
    vi.mocked(listCalendars).mockResolvedValue([
      { id: 'cal-primary', is_primary: true, my_role: 'owner', title: 'Основной' } as never,
    ])
    vi.mocked(createEvent).mockResolvedValue({ id: 'ev-new' } as never)
    await ensureGuidedTourDemoEvent('me')
    const body = vi.mocked(createEvent).mock.calls[0]?.[0] as { attendees: { user_sub: string }[] }
    expect(body.attendees).toEqual([{ user_sub: 'me' }])
  })

  it('cleanupGuidedTourDemoEvent swallows delete errors', async () => {
    vi.mocked(deleteEvent).mockRejectedValue(new Error('gone'))
    await expect(cleanupGuidedTourDemoEvent('x')).resolves.toBeUndefined()
  })

  it('stepNeedsTourDemoEvent detects calendar event steps', () => {
    expect(stepNeedsTourDemoEvent({ id: 'calendar-event' })).toBe(true)
    expect(stepNeedsTourDemoEvent({ id: 'calendar-event-detail' })).toBe(true)
    expect(stepNeedsTourDemoEvent({ id: 'calendar-event-edit-form' })).toBe(true)
    expect(stepNeedsTourDemoEvent({ id: 'calendar-grid' })).toBe(true)
    expect(stepNeedsTourDemoEvent({ id: 'calendar-create-event' })).toBe(false)
  })

  it('calendarTourEventLocationMatches distinguishes detail vs edit', () => {
    const id = 'ev-1'
    expect(calendarTourEventHref(id, false)).toBe('/calendar?event=ev-1')
    expect(calendarTourEventHref(id, true)).toBe('/calendar?event=ev-1&edit=1')
    expect(calendarTourEventLocationMatches('/calendar', '?event=ev-1', id, false)).toBe(true)
    expect(calendarTourEventLocationMatches('/calendar', '?event=ev-1&edit=1', id, false)).toBe(
      false,
    )
    expect(calendarTourEventLocationMatches('/calendar', '?event=ev-1&edit=1', id, true)).toBe(true)
  })

  it('buildTourDemoEventWindow spans one hour', () => {
    const { startsAt, endsAt } = buildTourDemoEventWindow(new Date('2030-06-15T08:00:00'))
    expect(new Date(endsAt).getTime() - new Date(startsAt).getTime()).toBe(60 * 60 * 1000)
  })
})
