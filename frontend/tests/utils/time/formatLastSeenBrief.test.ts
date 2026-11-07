import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { formatLastSeenBrief } from '@/utils/time/formatLastSeenBrief'

describe('formatLastSeenBrief', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-06-15T12:00:00Z'))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('невалидная дата → Не в сети', () => {
    expect(formatLastSeenBrief('not-a-date')).toBe('Не в сети')
  })

  it('меньше 15 секунд → только что', () => {
    expect(formatLastSeenBrief('2026-06-15T11:59:50Z')).toBe('Был(а) только что')
  })

  it('минуты / часы / дни', () => {
    expect(formatLastSeenBrief('2026-06-15T11:55:00Z')).toMatch(/^Был\(а\) /)
    expect(formatLastSeenBrief('2026-06-15T09:00:00Z')).toMatch(/^Был\(а\) /)
    expect(formatLastSeenBrief('2026-06-13T12:00:00Z')).toMatch(/^Был\(а\) /)
  })
})
