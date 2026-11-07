import { describe, expect, it } from 'vitest'

import { DEFAULT_CALENDAR_COLOR, toColorInputValue } from '../../../src/domain/calendar/calendarColor'

describe('toColorInputValue', () => {
  it('пропускает #rrggbb как есть', () => {
    expect(toColorInputValue('#8B5CF6')).toBe('#8B5CF6')
    expect(toColorInputValue('#ff0000')).toBe('#ff0000')
  })

  it('расширяет #rgb до #rrggbb (с сохранением регистра)', () => {
    expect(toColorInputValue('#abc')).toBe('#aabbcc')
    expect(toColorInputValue('#ABC')).toBe('#AABBCC')
    expect(toColorInputValue('#1a2b3c')).toBe('#1a2b3c')
  })

  it('возвращает дефолт для невалидного значения', () => {
    expect(toColorInputValue('')).toBe(DEFAULT_CALENDAR_COLOR)
    expect(toColorInputValue('not-a-color')).toBe(DEFAULT_CALENDAR_COLOR)
    expect(toColorInputValue('#1234')).toBe(DEFAULT_CALENDAR_COLOR)
    expect(toColorInputValue('rgb(1,2,3)')).toBe(DEFAULT_CALENDAR_COLOR)
  })

  it('тримит пробелы вокруг валидного hex', () => {
    expect(toColorInputValue('  #8B5CF6  ')).toBe('#8B5CF6')
  })
})

describe('DEFAULT_CALENDAR_COLOR', () => {
  it('валидный #rrggbb', () => {
    expect(/^#[0-9A-Fa-f]{6}$/.test(DEFAULT_CALENDAR_COLOR)).toBe(true)
  })
})
