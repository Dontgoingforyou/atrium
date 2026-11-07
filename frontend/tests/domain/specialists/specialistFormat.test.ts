import { describe, expect, it } from 'vitest'

import { formatBirthdate, formatSyncedAt } from '../../../src/domain/specialists/specialistFormat'

describe('formatBirthdate', () => {
  it('преобразует yyyy-mm-dd в dd-mm-yyyy', () => {
    expect(formatBirthdate('1990-05-12')).toBe('12-05-1990')
  })

  it('возвращает пустую строку для null/undefined', () => {
    expect(formatBirthdate(null)).toBe('')
    expect(formatBirthdate(undefined)).toBe('')
  })

  it('возвращает пустую строку для пустой строки', () => {
    expect(formatBirthdate('')).toBe('')
  })

  it('переставляет любую 3-сегментную дату, даже если это не yyyy-mm-dd', () => {
    // Функция не валидирует семантику, а только меняет порядок сегментов,
    // как оригинальный inline-код. Это документированное поведение.
    expect(formatBirthdate('12-05-1990')).toBe('1990-05-12')
  })

  it('возвращает исходное значение при неполной дате', () => {
    expect(formatBirthdate('1990-05')).toBe('1990-05')
    expect(formatBirthdate('1990')).toBe('1990')
  })
})

describe('formatSyncedAt', () => {
  it('возвращает прочерк для null/undefined', () => {
    expect(formatSyncedAt(null)).toBe('—')
    expect(formatSyncedAt(undefined)).toBe('—')
  })

  it('возвращает прочерк для пустой строки', () => {
    expect(formatSyncedAt('')).toBe('—')
  })

  it('форматирует корректную ISO-дату в локальную строку', () => {
    const result = formatSyncedAt('2024-01-15T10:30:00Z')
    expect(result).not.toBe('—')
    expect(result).not.toBe('2024-01-15T10:30:00Z')
    expect(result.length).toBeGreaterThan(0)
  })

  it('возвращает исходное значение для неразбираемой даты', () => {
    const raw = 'not-a-date'
    expect(formatSyncedAt(raw)).toBe(raw)
  })
})
