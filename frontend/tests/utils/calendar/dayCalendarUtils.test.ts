import { describe, expect, it } from 'vitest'
import {
  buildMonthDayGrid,
  dateStrFromParts,
  formatDayCalendarLabel,
  isDateDisabled,
  parseDateStr,
} from '@/utils/calendar/dayCalendarUtils'

describe('parseDateStr / dateStrFromParts', () => {
  it('round-trip для валидной даты', () => {
    const parts = { year: 2026, monthIndex: 5, day: 10 }
    const iso = dateStrFromParts(parts.year, parts.monthIndex, parts.day)
    expect(iso).toBe('2026-06-10')
    expect(parseDateStr(iso)).toEqual(parts)
  })

  it('отклоняет невалидную дату', () => {
    expect(parseDateStr('2026-02-30')).toBeNull()
    expect(parseDateStr('')).toBeNull()
  })
})

describe('formatDayCalendarLabel', () => {
  it('форматирует дату по-русски', () => {
    expect(formatDayCalendarLabel('2026-06-10')).toBe('10 июня 2026')
  })

  it('пустая строка для пустого значения', () => {
    expect(formatDayCalendarLabel('')).toBe('')
  })
})

describe('buildMonthDayGrid', () => {
  it('возвращает 42 ячейки', () => {
    const grid = buildMonthDayGrid(2026, 5)
    expect(grid).toHaveLength(42)
  })

  it('июнь 2026 начинается с понедельника 1-го', () => {
    const grid = buildMonthDayGrid(2026, 5)
    const firstInMonth = grid.find((c) => c.dateStr === '2026-06-01')
    expect(firstInMonth).toBeDefined()
    expect(firstInMonth!.outsideMonth).toBe(false)
    expect(firstInMonth!.day).toBe(1)
  })

  it('март 2026 начинается в воскресенье — первая ячейка из февраля', () => {
    const grid = buildMonthDayGrid(2026, 2)
    expect(grid[0].outsideMonth).toBe(true)
    expect(grid[0].dateStr).toBe('2026-02-23')
    const mar1 = grid.find((c) => c.dateStr === '2026-03-01')
    expect(mar1?.outsideMonth).toBe(false)
  })

  it('все dateStr уникальны в сетке', () => {
    const grid = buildMonthDayGrid(2026, 0)
    const ids = grid.map((c) => c.dateStr)
    expect(new Set(ids).size).toBe(42)
  })
})

describe('isDateDisabled', () => {
  it('блокирует даты до minDate', () => {
    expect(isDateDisabled('2026-06-09', '2026-06-10')).toBe(true)
    expect(isDateDisabled('2026-06-10', '2026-06-10')).toBe(false)
  })

  it('блокирует даты после maxDate', () => {
    expect(isDateDisabled('2026-06-11', undefined, '2026-06-10')).toBe(true)
    expect(isDateDisabled('2026-06-10', undefined, '2026-06-10')).toBe(false)
  })
})
