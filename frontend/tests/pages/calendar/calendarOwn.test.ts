import { describe, expect, it } from 'vitest'

import {
  canDragCalendarOccurrence,
  canEditCalendarOccurrence,
  defaultOwnCalendarId,
  ownCalendars,
} from '../../../src/pages/calendar/calendarOwn'
import type { PortalCalendar } from '../../../src/types/calendar'

function makeCal(over: Partial<PortalCalendar> = {}): PortalCalendar {
  return {
    id: 'cal-1',
    owner_sub: 'sub-1',
    title: 'Календарь',
    color: '#8B5CF6',
    timezone: 'UTC',
    is_primary: false,
    show_to_other_departments: false,
    my_role: 'owner',
    created_at: '',
    updated_at: '',
    members: [],
    ...over,
  }
}

describe('ownCalendars', () => {
  it('оставляет только календари с my_role=owner', () => {
    const list = [
      makeCal({ id: 'a', my_role: 'owner' }),
      makeCal({ id: 'b', my_role: 'editor' }),
      makeCal({ id: 'c', my_role: 'viewer' }),
    ]
    expect(ownCalendars(list).map((c) => c.id)).toEqual(['a'])
  })

  it('возвращает пустой массив для пустого входа', () => {
    expect(ownCalendars([])).toEqual([])
  })
})

describe('defaultOwnCalendarId', () => {
  it('предпочитает primary-календарь владельца', () => {
    const list = [
      makeCal({ id: 'a', my_role: 'owner', is_primary: false }),
      makeCal({ id: 'b', my_role: 'owner', is_primary: true }),
    ]
    expect(defaultOwnCalendarId(list)).toBe('b')
  })

  it('берёт первый календарь владельца, если нет primary', () => {
    const list = [makeCal({ id: 'a', my_role: 'owner', is_primary: false })]
    expect(defaultOwnCalendarId(list)).toBe('a')
  })

  it('возвращает пустую строку, если нет календарей владельца', () => {
    const list = [makeCal({ id: 'a', my_role: 'editor' })]
    expect(defaultOwnCalendarId(list)).toBe('')
  })

  it('возвращает пустую строку для пустого входа', () => {
    expect(defaultOwnCalendarId([])).toBe('')
  })
})

describe('canEditCalendarOccurrence', () => {
  it('разрешает организатору в peer-view', () => {
    expect(
      canEditCalendarOccurrence(
        { organizer_sub: 'me', is_peer_view: true },
        'me',
        null,
      ),
    ).toBe(true)
  })

  it('запрещает чужое событие в peer-view даже с ролью owner', () => {
    expect(
      canEditCalendarOccurrence(
        { organizer_sub: 'other', is_peer_view: true },
        'me',
        'owner',
      ),
    ).toBe(false)
  })

  it('разрешает owner и editor в своём календаре', () => {
    const occ = { organizer_sub: 'other', is_peer_view: false }
    expect(canEditCalendarOccurrence(occ, 'me', 'owner')).toBe(true)
    expect(canEditCalendarOccurrence(occ, 'me', 'editor')).toBe(true)
  })

  it('запрещает viewer в своём календаре, если не организатор', () => {
    expect(
      canEditCalendarOccurrence(
        { organizer_sub: 'other', is_peer_view: false },
        'me',
        'viewer',
      ),
    ).toBe(false)
  })

  it('не даёт тащить отменённое вхождение и чужой просмотр', () => {
    expect(
      canDragCalendarOccurrence(
        { organizer_sub: 'me', is_cancelled: true },
        'me',
        'owner',
      ),
    ).toBe(false)
    expect(
      canDragCalendarOccurrence(
        { organizer_sub: 'other', is_peer_view: true },
        'me',
        'owner',
      ),
    ).toBe(false)
    expect(
      canDragCalendarOccurrence({ organizer_sub: 'other' }, 'me', 'editor'),
    ).toBe(true)
  })

  it('запрещает без пользователя или без события', () => {
    expect(canEditCalendarOccurrence({ organizer_sub: 'me' }, null, 'owner')).toBe(false)
    expect(canEditCalendarOccurrence(null, 'me', 'owner')).toBe(false)
  })
})
