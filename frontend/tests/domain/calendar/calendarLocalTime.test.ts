import { describe, expect, it } from 'vitest'

import { plusOneHourLocal } from '../../../src/domain/calendar/calendarLocalTime'

describe('plusOneHourLocal', () => {
  it('сдвигает время начала на один час в тот же день', () => {
    expect(plusOneHourLocal('2026-10-02', '18:00')).toEqual({
      date: '2026-10-02',
      time: '19:00',
    })
  })

  it('переносит дату на следующий день через полночь', () => {
    expect(plusOneHourLocal('2026-10-02', '23:30')).toEqual({
      date: '2026-10-03',
      time: '00:30',
    })
  })

  it('переносит дату на следующий месяц', () => {
    expect(plusOneHourLocal('2026-01-31', '23:30')).toEqual({
      date: '2026-02-01',
      time: '00:30',
    })
  })
})
