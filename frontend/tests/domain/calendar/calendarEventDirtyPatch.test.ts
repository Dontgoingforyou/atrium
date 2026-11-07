import { describe, expect, it } from 'vitest'

import { buildCalendarEventDirtyPatch } from '@/domain/calendar/calendarEventDirtyPatch'
import type { CalendarEventFormSnapshot } from '@/domain/calendar/calendarEventDirtyPatch'

function snapshot(over: Partial<CalendarEventFormSnapshot> = {}): CalendarEventFormSnapshot {
  return {
    title: 'Дейлик',
    description: null,
    location: null,
    starts_at: '2026-09-14T07:00:00.000Z',
    ends_at: '2026-09-14T08:00:00.000Z',
    rrule: null,
    color: '#EC4899',
    attendees: [{ user_sub: 'author' }, { user_sub: 'manager' }],
    reminders: [{ offset_minutes: 15 }],
    ...over,
  }
}

describe('buildCalendarEventDirtyPatch', () => {
  it('при смене только цвета возвращает только color', () => {
    const initial = snapshot()
    const current = snapshot({ color: '#14B8A6' })
    expect(buildCalendarEventDirtyPatch(initial, current)).toEqual({ color: '#14B8A6' })
  })

  it('при смене названия и цвета возвращает оба поля', () => {
    const initial = snapshot()
    const current = snapshot({ title: 'Синок', color: '#14B8A6' })
    expect(buildCalendarEventDirtyPatch(initial, current)).toEqual({
      title: 'Синок',
      color: '#14B8A6',
    })
  })

  it('не кладёт в PATCH дефолтный reminder и lossy rrule, если пользователь их не менял', () => {
    const initial = snapshot({
      rrule: 'FREQ=WEEKLY',
      reminders: [{ offset_minutes: 15 }],
    })
    const current = snapshot({
      rrule: 'FREQ=WEEKLY',
      reminders: [{ offset_minutes: 15 }],
      color: '#14B8A6',
    })
    const patch = buildCalendarEventDirtyPatch(initial, current)
    expect(patch).toEqual({ color: '#14B8A6' })
    expect(patch).not.toHaveProperty('reminders')
    expect(patch).not.toHaveProperty('rrule')
  })

  it('считает attendees и reminders множествами, порядок не важен', () => {
    const initial = snapshot({
      attendees: [{ user_sub: 'manager' }, { user_sub: 'author' }],
      reminders: [{ offset_minutes: 60 }, { offset_minutes: 15 }],
    })
    const current = snapshot({
      attendees: [{ user_sub: 'author' }, { user_sub: 'manager' }],
      reminders: [{ offset_minutes: 15 }, { offset_minutes: 60 }],
    })
    expect(buildCalendarEventDirtyPatch(initial, current)).toEqual({})
  })

  it('включает reminders и rrule, если пользователь их изменил', () => {
    const initial = snapshot({ rrule: null, reminders: [{ offset_minutes: 15 }] })
    const current = snapshot({
      rrule: 'FREQ=DAILY',
      reminders: [{ offset_minutes: 60 }],
    })
    expect(buildCalendarEventDirtyPatch(initial, current)).toEqual({
      rrule: 'FREQ=DAILY',
      reminders: [{ offset_minutes: 60 }],
    })
  })
})
