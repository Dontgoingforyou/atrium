// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  isSafeExternalUrl,
  openExternalUrl,
  safeExternalUrl,
} from '../../src/utils/safeExternalUrl'

afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

describe('isSafeExternalUrl', () => {
  it('https и http допустимы без allowlist', () => {
    expect(isSafeExternalUrl('https://example.com/a')).toBe(true)
    expect(isSafeExternalUrl('http://example.com')).toBe(true)
  })

  it('javascript: и data: → false', () => {
    expect(isSafeExternalUrl('javascript:alert(1)')).toBe(false)
    expect(isSafeExternalUrl('data:text/html,hi')).toBe(false)
  })

  it('protocol-relative, file:, vbscript: → false', () => {
    expect(isSafeExternalUrl('//evil.example/x')).toBe(false)
    expect(isSafeExternalUrl('file:///etc/passwd')).toBe(false)
    expect(isSafeExternalUrl('vbscript:msgbox(1)')).toBe(false)
  })

  it('невалидный URL → false', () => {
    expect(isSafeExternalUrl('not a url')).toBe(false)
  })

  it('restrictToAllowlist: только telegram-домены', () => {
    expect(isSafeExternalUrl('https://t.me/u', { restrictToAllowlist: true })).toBe(true)
    expect(isSafeExternalUrl('https://web.telegram.org/a', { restrictToAllowlist: true })).toBe(
      true,
    )
    expect(isSafeExternalUrl('https://evil.com', { restrictToAllowlist: true })).toBe(false)
  })
})

describe('safeExternalUrl', () => {
  it('null/пусто → undefined', () => {
    expect(safeExternalUrl(null)).toBeUndefined()
    expect(safeExternalUrl('')).toBeUndefined()
  })

  it('безопасный URL возвращает исходную строку', () => {
    expect(safeExternalUrl('https://t.me/x')).toBe('https://t.me/x')
  })

  it('небезопасный → undefined', () => {
    expect(safeExternalUrl('javascript:alert(1)')).toBeUndefined()
  })
})

describe('openExternalUrl', () => {
  it('блокирует небезопасный URL и не вызывает window.open', () => {
    const open = vi.fn()
    vi.stubGlobal('open', open)

    expect(openExternalUrl('javascript:alert(1)')).toBe(false)
    expect(open).not.toHaveBeenCalled()
  })

  it('открывает безопасный URL с noopener', () => {
    const fakeWin = { opener: 'keep' as unknown as null }
    const open = vi.fn(() => fakeWin)
    vi.stubGlobal('open', open)

    expect(openExternalUrl('https://example.com')).toBe(true)
    expect(open).toHaveBeenCalledWith('https://example.com', '_blank', 'noopener,noreferrer')
    expect(fakeWin.opener).toBeNull()
  })
})
