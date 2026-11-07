import { describe, expect, it } from 'vitest'

import {
  applyOccurrenceDayMove,
  calendarDayDropId,
  parseCalendarDayDropId,
  planOccurrenceDayMove,
} from '@/domain/calendar/occurrenceDayMove'
import type { PortalCalendarOccurrence } from '@/types/calendar'

type DayMoveSource = Parameters<typeof planOccurrenceDayMove>[0]

function occurrence(over: Partial<DayMoveSource> = {}): DayMoveSource {
  const start = new Date(2026, 10, 3, 17, 0, 0)
  const end = new Date(2026, 10, 3, 18, 0, 0)
  return {
    event_id: 'event-1',
    calendar_id: 'cal-1',
    original_start: start.toISOString(),
    starts_at: start.toISOString(),
    ends_at: end.toISOString(),
    rrule: null,
    title: 'daily #1',
    description: null,
    location: null,
    ...over,
  }
}

describe('planOccurrenceDayMove', () => {
  it('переносит одиночное событие на другой день и оставляет местное время', () => {
    const plan = planOccurrenceDayMove(occurrence(), new Date(2026, 10, 4, 12, 0, 0))
    expect(plan?.kind).toBe('patch')
    expect(plan && new Date(plan.starts_at).getDate()).toBe(4)
    expect(plan && new Date(plan.starts_at).getHours()).toBe(17)
    expect(plan && new Date(plan.starts_at).getMinutes()).toBe(0)
    expect(plan && plan.ends_at && new Date(plan.ends_at).getHours()).toBe(18)
    expect(plan && plan.ends_at && new Date(plan.ends_at).getDate()).toBe(4)
  })

  it('у повтора сдвигает только это вхождение и не трогает якорь серии', () => {
    const original = new Date(2026, 10, 3, 17, 0, 0).toISOString()
    const plan = planOccurrenceDayMove(
      occurrence({ rrule: 'FREQ=DAILY', original_start: original }),
      new Date(2026, 10, 4),
    )
    expect(plan?.kind).toBe('override')
    if (plan?.kind !== 'override') return
    expect(plan.original_start).toBe(original)
    expect(plan.title).toBe('daily #1')
    expect(new Date(plan.starts_at).getDate()).toBe(4)
    expect(new Date(plan.starts_at).getHours()).toBe(17)
  })

  it('не строит запрос, если день тот же', () => {
    expect(planOccurrenceDayMove(occurrence(), new Date(2026, 10, 3, 9, 0, 0))).toBeNull()
  })

  it('сохраняет переход через полночь', () => {
    const start = new Date(2026, 10, 3, 23, 0, 0)
    const end = new Date(2026, 10, 4, 1, 0, 0)
    const plan = planOccurrenceDayMove(
      occurrence({
        starts_at: start.toISOString(),
        ends_at: end.toISOString(),
        original_start: start.toISOString(),
      }),
      new Date(2026, 10, 5),
    )
    expect(plan && new Date(plan.starts_at).getDate()).toBe(5)
    expect(plan && new Date(plan.starts_at).getHours()).toBe(23)
    expect(plan && plan.ends_at && new Date(plan.ends_at).getDate()).toBe(6)
    expect(plan && plan.ends_at && new Date(plan.ends_at).getHours()).toBe(1)
  })

  it('отклоняет битую дату начала', () => {
    expect(planOccurrenceDayMove(occurrence({ starts_at: 'not-a-date' }), new Date(2026, 10, 4))).toBeNull()
  })
})

describe('applyOccurrenceDayMove', () => {
  it('меняет только перетащенное вхождение серии', () => {
    const tuesday = new Date(2026, 10, 3, 17, 0, 0).toISOString()
    const nextTuesday = new Date(2026, 10, 10, 17, 0, 0).toISOString()
    const moved = new Date(2026, 10, 4, 17, 0, 0).toISOString()
    const items = [
      { event_id: 'event-1', original_start: tuesday, starts_at: tuesday },
      { event_id: 'event-1', original_start: nextTuesday, starts_at: nextTuesday },
    ] as PortalCalendarOccurrence[]
    const next = applyOccurrenceDayMove(items, {
      kind: 'override',
      event_id: 'event-1',
      calendar_id: 'cal-1',
      original_start: tuesday,
      starts_at: moved,
      ends_at: null,
      title: 'daily #1',
      description: null,
      location: null,
    })
    expect(next[0]?.starts_at).toBe(moved)
    expect(next[1]?.starts_at).toBe(nextTuesday)
  })
})

describe('calendarDayDropId', () => {
  it('кодирует и разбирает местный день', () => {
    const day = new Date(2026, 10, 4)
    const id = calendarDayDropId(day)
    const parsed = parseCalendarDayDropId(id)
    expect(parsed?.getFullYear()).toBe(2026)
    expect(parsed?.getMonth()).toBe(10)
    expect(parsed?.getDate()).toBe(4)
  })

  it('не принимает чужой идентификатор и несуществующий день', () => {
    expect(parseCalendarDayDropId('cal-occ:1')).toBeNull()
    expect(parseCalendarDayDropId('cal-day:2026-02-31')).toBeNull()
  })
})
