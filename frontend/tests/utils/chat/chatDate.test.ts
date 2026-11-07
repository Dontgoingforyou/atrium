import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  dayDividerLabelForDate,
  sameCalendarDay,
  timeOnly,
} from '../../../src/utils/chat/chatDate'

/** Локальный полдень → ISO, чтобы calendar day не зависел от TZ раннера. */
function localNoonIso(year: number, monthIndex: number, day: number): string {
  return new Date(year, monthIndex, day, 12, 0, 0).toISOString()
}

describe('chatDate', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date(2026, 5, 15, 15, 0, 0))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('dayDividerLabelForDate: Сегодня / Вчера / дата', () => {
    expect(dayDividerLabelForDate(localNoonIso(2026, 5, 15))).toBe('Сегодня')
    expect(dayDividerLabelForDate(localNoonIso(2026, 5, 14))).toBe('Вчера')
    expect(dayDividerLabelForDate(localNoonIso(2026, 2, 1))).toMatch(/марта/i)
    expect(dayDividerLabelForDate(localNoonIso(2024, 2, 1))).toMatch(/2024/)
    expect(dayDividerLabelForDate('')).toBe('—')
  })

  it('timeOnly форматирует время или —', () => {
    expect(timeOnly(localNoonIso(2026, 5, 15))).toMatch(/\d{2}:\d{2}/)
    expect(timeOnly('')).toBe('—')
  })

  it('sameCalendarDay', () => {
    expect(sameCalendarDay(localNoonIso(2026, 5, 15), localNoonIso(2026, 5, 15))).toBe(true)
    expect(sameCalendarDay(localNoonIso(2026, 5, 15), localNoonIso(2026, 5, 14))).toBe(false)
    expect(sameCalendarDay('', localNoonIso(2026, 5, 15))).toBe(false)
  })
})
