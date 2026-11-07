import { describe, expect, it } from 'vitest'

import {
  MONTHS_FULL,
  MONTHS_SHORT,
  formatMonthCalendarLabel,
  isMonthDisabled,
  monthStrFromCalendarValue,
  monthStrFromValue,
  monthStrToCalendarValue,
  parseMonthStr,
  yearPageStart,
  yearsInPage,
} from '@/utils/calendar/monthCalendarUtils'

describe('monthCalendarUtils', () => {
  it('parseMonthStr / monthStrFromValue round-trip', () => {
    expect(parseMonthStr('2026-03')).toEqual({ year: 2026, monthIndex: 2 })
    expect(parseMonthStr('bad')).toBeNull()
    expect(parseMonthStr('2026-13')).toBeNull()
    expect(monthStrFromValue({ year: 2026, monthIndex: 2 })).toBe('2026-03')
    expect(monthStrFromCalendarValue({ year: 2026, monthIndex: 0 })).toBe('2026-01')
  })

  it('formatMonthCalendarLabel', () => {
    expect(formatMonthCalendarLabel({ year: 2026, monthIndex: 0 })).toBe('Январь 2026')
    expect(formatMonthCalendarLabel({ year: 2026, monthIndex: 8 })).toBe('Сентябрь 2026')
  })

  it('сетка месяцев — короткие подписи, иначе 4 колонки наезжают', () => {
    expect(MONTHS_SHORT).toHaveLength(12)
    expect(MONTHS_FULL).toHaveLength(12)
    for (const short of MONTHS_SHORT) {
      expect(short.length).toBeLessThanOrEqual(3)
    }
    expect(MONTHS_SHORT[1]).toBe('Фев')
    expect(MONTHS_SHORT[8]).toBe('Сен')
    expect(MONTHS_FULL[1]).toBe('Февраль')
  })

  it('monthStrToCalendarValue с fallback', () => {
    expect(monthStrToCalendarValue('2026-07')).toEqual({ year: 2026, monthIndex: 6 })
    const fb = new Date(2025, 4, 1)
    expect(monthStrToCalendarValue('x', fb)).toEqual({ year: 2025, monthIndex: 4 })
  })

  it('isMonthDisabled по min/max', () => {
    expect(isMonthDisabled(2026, 5, '2026-03', '2026-08')).toBe(false)
    expect(isMonthDisabled(2026, 0, '2026-03', '2026-08')).toBe(true)
    expect(isMonthDisabled(2026, 10, '2026-03', '2026-08')).toBe(true)
  })

  it('yearPageStart выравнивает год к началу страницы по 12', () => {
    expect(yearPageStart(2026)).toBe(2016)
    expect(yearPageStart(2020)).toBe(2016)
    expect(yearPageStart(2016)).toBe(2016)
    expect(yearPageStart(2015)).toBe(2004)
    expect(yearPageStart(0)).toBe(0)
  })

  it('yearsInPage возвращает 12 лет от старта страницы', () => {
    expect(yearsInPage(2016)).toEqual([
      2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026, 2027,
    ])
    expect(yearsInPage(yearPageStart(2026))).toContain(2026)
    expect(yearsInPage(2004)).toHaveLength(12)
  })
})
