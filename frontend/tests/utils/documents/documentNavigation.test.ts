import { QueryClient } from '@tanstack/react-query'
import { describe, expect, it, vi } from 'vitest'

vi.mock('@/api/documents/documentsApi', () => ({
  getDocument: vi.fn(),
}))

import { getDocument } from '@/api/documents/documentsApi'
import {
  documentIdsMatch,
  navigateToPortalDocument,
  normalizeDocumentId,
  portalDocumentHref,
  portalDocumentQueryKey,
} from '@/utils/documents/documentNavigation'

describe('documentNavigation', () => {
  it('normalizeDocumentId обрезает пробелы и приводит к нижнему регистру', () => {
    expect(normalizeDocumentId('  AAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE  ')).toBe(
      'aaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
    )
  })

  it('normalizeDocumentId: null / undefined / пустая строка → пустая строка', () => {
    expect(normalizeDocumentId(null)).toBe('')
    expect(normalizeDocumentId(undefined)).toBe('')
    expect(normalizeDocumentId('')).toBe('')
  })

  it('documentIdsMatch игнорирует регистр', () => {
    expect(
      documentIdsMatch('da9d2d56-dabe-4fe4-a694-b31b3fb32334', 'DA9D2D56-DABE-4FE4-A694-B31B3FB32334'),
    ).toBe(true)
  })

  it('documentIdsMatch: пустая строка и null совпадают (оба → пустая строка)', () => {
    expect(documentIdsMatch('', null)).toBe(true)
    expect(documentIdsMatch(null, undefined)).toBe(true)
  })

  it('portalDocumentHref кодирует спецсимволы в id', () => {
    const id = 'foo/../bar'
    expect(portalDocumentHref(id)).toBe(`/documents/${encodeURIComponent(id)}`)
    expect(portalDocumentHref(id)).not.toContain('../')
  })

  it('navigateToPortalDocument всё равно вызывает navigate, если prefetch упал', async () => {
    vi.mocked(getDocument).mockRejectedValue(new Error('сеть'))
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const navigate = vi.fn()

    await navigateToPortalDocument(navigate, qc, 'doc-1')

    expect(navigate).toHaveBeenCalledWith('/documents/doc-1')
  })

  it('при падении prefetch снимает error-state query документа', async () => {
    vi.mocked(getDocument).mockRejectedValue(new Error('сеть'))
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    qc.setQueryData(portalDocumentQueryKey('doc-1'), { id: 'doc-1' })

    await navigateToPortalDocument(vi.fn(), qc, 'doc-1')

    expect(qc.getQueryData(portalDocumentQueryKey('doc-1'))).toBeUndefined()
  })

  it('navigate кодирует id с ../', async () => {
    vi.mocked(getDocument).mockResolvedValue({ id: '../x' } as never)
    const navigate = vi.fn()
    await navigateToPortalDocument(navigate, new QueryClient(), '../x')
    expect(navigate).toHaveBeenCalledWith(`/documents/${encodeURIComponent('../x')}`)
  })
})
