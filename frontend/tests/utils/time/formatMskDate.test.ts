import { describe, expect, it } from 'vitest'

import { formatMskDate } from '@/utils/time/formatMskDate'

describe('formatMskDate', () => {
  it('невалидная дата возвращается как есть', () => {
    expect(formatMskDate('not-a-date')).toBe('not-a-date')
  })

  it('UTC-дата форматируется в dd.mm.yyyy по МСК', () => {
    // 2026-01-15T00:00:00Z → 15.01.2026 в любой таймзоне МСК (UTC+3)
    expect(formatMskDate('2026-01-15T00:00:00Z')).toBe('15.01.2026')
  })

  it('дата на границе суток в UTC попадает в ту же календарную дату МСК', () => {
    // 2026-01-15T21:00:00Z → 16.01.2026 00:00 по МСК — календарная дата 16.01
    expect(formatMskDate('2026-01-15T21:00:00Z')).toBe('16.01.2026')
  })

  it('дата без зоны трактуется как UTC', () => {
    expect(formatMskDate('2026-03-08T12:00:00')).toBe('08.03.2026')
  })
})
