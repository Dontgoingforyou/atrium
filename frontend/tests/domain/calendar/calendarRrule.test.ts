import { describe, expect, it } from 'vitest'

import {
  addDays,
  endOfMonth,
  formatDayLabel,
  formatTime,
  presetFromRrule,
  rruleFromPreset,
  startOfMonth,
  startOfWeek,
  toIso,
} from '../../../src/domain/calendar/calendarRrule'

describe('calendarRrule presets', () => {
  it('строит RRULE из пресетов', () => {
    expect(rruleFromPreset('none')).toBeNull()
    expect(rruleFromPreset('daily')).toBe('FREQ=DAILY')
    expect(rruleFromPreset('weekdays')).toBe('FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR')
    expect(rruleFromPreset('weekly')).toBe('FREQ=WEEKLY')
    expect(rruleFromPreset('monthly')).toBe('FREQ=MONTHLY')
  })

  it('распознаёт пресет из RRULE', () => {
    expect(presetFromRrule(null)).toBe('none')
    expect(presetFromRrule('FREQ=DAILY')).toBe('daily')
    expect(presetFromRrule('FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR')).toBe('weekdays')
    expect(presetFromRrule('FREQ=WEEKLY')).toBe('weekly')
    expect(presetFromRrule('FREQ=MONTHLY')).toBe('monthly')
    expect(presetFromRrule('FREQ=YEARLY')).toBe('none')
  })
})

describe('calendarRrule date helpers', () => {
  it('startOfMonth / endOfMonth', () => {
    const d = new Date(2026, 2, 15) // March
    expect(startOfMonth(d).getDate()).toBe(1)
    expect(startOfMonth(d).getMonth()).toBe(2)
    expect(endOfMonth(d).getMonth()).toBe(3)
    expect(endOfMonth(d).getDate()).toBe(1)
  })

  it('startOfWeek — понедельник', () => {
    // Wednesday 2026-03-18
    const wed = new Date(2026, 2, 18)
    const mon = startOfWeek(wed)
    expect(mon.getDay()).toBe(1)
    expect(mon.getDate()).toBe(16)
    expect(mon.getHours()).toBe(0)
  })

  it('addDays и toIso', () => {
    const d = new Date(Date.UTC(2026, 0, 1))
    const next = addDays(d, 2)
    expect(next.getUTCDate()).toBe(3)
    expect(toIso(d)).toMatch(/^2026-01-01T/)
  })

  it('formatDayLabel / formatTime — непустые строки', () => {
    const d = new Date(2026, 0, 5)
    expect(formatDayLabel(d).length).toBeGreaterThan(0)
    expect(formatTime('2026-01-05T14:30:00Z')).toMatch(/\d/)
  })
})
