import { describe, expect, it } from 'vitest'

import { normalizeHttpUrl } from '@/utils/html/normalizeHttpUrl'

describe('normalizeHttpUrl', () => {
  it('домен без схемы → https://', () => {
    expect(normalizeHttpUrl('qualify.su')).toBe('https://qualify.su/')
  })

  it('полный https URL с путём сохраняет путь', () => {
    expect(normalizeHttpUrl('https://example.com/a/b')).toBe('https://example.com/a/b')
  })

  it('http URL допускается', () => {
    expect(normalizeHttpUrl('http://example.com')).toBe('http://example.com/')
  })

  it('javascript: → null', () => {
    expect(normalizeHttpUrl('javascript:alert(1)')).toBeNull()
  })

  it('data: → null', () => {
    expect(normalizeHttpUrl('data:text/html,hi')).toBeNull()
  })

  it('пусто / пробелы → пустая строка', () => {
    expect(normalizeHttpUrl('')).toBe('')
    expect(normalizeHttpUrl('   ')).toBe('')
  })

  it('невалидный ввод → null', () => {
    expect(normalizeHttpUrl('not a url')).toBeNull()
  })

  it('protocol-relative и vbscript → null', () => {
    expect(normalizeHttpUrl('//evil.example/x')).toBeNull()
    expect(normalizeHttpUrl('vbscript:x')).toBeNull()
  })
})
