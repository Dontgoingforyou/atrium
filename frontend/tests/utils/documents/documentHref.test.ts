import { describe, expect, it, vi } from 'vitest'

import { getDocumentPublicHref, getDocumentPublicUrl } from '@/utils/documents/documentHref'

describe('documentHref', () => {
  it('getDocumentPublicHref без slug', () => {
    expect(getDocumentPublicHref('abc-123')).toBe('/documents/abc-123')
  })

  it('getDocumentPublicHref со slug раздела', () => {
    expect(getDocumentPublicHref('abc-123', 'outstaff')).toBe('/p/outstaff/documents/abc-123')
  })

  it('пустой slug даёт путь без /p/', () => {
    expect(getDocumentPublicHref('abc-123', '')).toBe('/documents/abc-123')
    expect(getDocumentPublicHref('abc-123', null)).toBe('/documents/abc-123')
  })

  it('кодирует id и slug с / и ../ (не open redirect)', () => {
    const id = '../evil/path'
    const slug = 'a/../b'
    expect(getDocumentPublicHref(id)).toBe(`/documents/${encodeURIComponent(id)}`)
    expect(getDocumentPublicHref(id, slug)).toBe(
      `/p/${encodeURIComponent(slug)}/documents/${encodeURIComponent(id)}`,
    )
    expect(getDocumentPublicHref(id)).not.toContain('../')
    expect(getDocumentPublicHref(id, slug)).not.toContain('../')
  })

  it('getDocumentPublicUrl добавляет origin', () => {
    vi.stubGlobal('window', { location: { origin: 'https://portal.test' } })
    expect(getDocumentPublicUrl('abc-123')).toBe('https://portal.test/documents/abc-123')
  })
})
