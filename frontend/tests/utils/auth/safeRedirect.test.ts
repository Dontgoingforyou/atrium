// @vitest-environment jsdom

import { beforeEach, describe, expect, it } from 'vitest'

import { sanitizeNextPath } from '@/utils/auth/safeRedirect'

beforeEach(() => {
  Object.defineProperty(window, 'location', {
    configurable: true,
    value: { origin: 'https://portal.test' },
  })
})

describe('sanitizeNextPath', () => {
  it('пустая строка → /', () => {
    expect(sanitizeNextPath('')).toBe('/')
  })

  it('относительный путь с query и hash сохраняется', () => {
    expect(sanitizeNextPath('/tasks?tab=mine#row')).toBe('/tasks?tab=mine#row')
  })

  it('обрезает пробелы по краям', () => {
    expect(sanitizeNextPath('  /docs  ')).toBe('/docs')
  })

  it('protocol-relative // → /', () => {
    expect(sanitizeNextPath('//evil.example/phish')).toBe('/')
  })

  it('backslash в начале или внутри → /', () => {
    expect(sanitizeNextPath('\\evil')).toBe('/')
    expect(sanitizeNextPath('/ok\\no')).toBe('/')
  })

  it('абсолютный URL чужого origin → /', () => {
    expect(sanitizeNextPath('https://evil.example/x')).toBe('/')
  })

  it('абсолютный URL того же origin → path+search+hash', () => {
    expect(sanitizeNextPath('https://portal.test/chats?id=1#m')).toBe('/chats?id=1#m')
  })

  it('опасные схемы и open-redirect классика → /', () => {
    expect(sanitizeNextPath('javascript:alert(1)')).toBe('/')
    expect(sanitizeNextPath('data:text/html,x')).toBe('/')
    expect(sanitizeNextPath('vbscript:x')).toBe('/')
    expect(sanitizeNextPath('https://portal.test@evil.example/')).toBe('/')
    expect(sanitizeNextPath('/\t/evil.example')).toBe('/')
  })
})
