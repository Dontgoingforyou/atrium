import { describe, expect, it } from 'vitest'

import { parseApiDateTime } from '@/utils/time/parseApiDateTime'
import { timeOnly } from '@/utils/chat/chatDate'

describe('parseApiDateTime', () => {
  it('парсит ISO с T и Z', () => {
    const d = parseApiDateTime('2024-06-15T14:30:00Z')
    expect(d).not.toBeNull()
    expect(d!.getUTCHours()).toBe(14)
  })

  it('нормализует пробел вместо T (Safari)', () => {
    const d = parseApiDateTime('2024-06-15 14:30:00')
    expect(d).not.toBeNull()
  })

  it('возвращает null для мусора', () => {
    expect(parseApiDateTime('undefined')).toBeNull()
    expect(parseApiDateTime('')).toBeNull()
  })
})

describe('timeOnly', () => {
  it('не возвращает Invalid Date для битой строки', () => {
    expect(timeOnly('not-a-date')).toBe('—')
  })
})
