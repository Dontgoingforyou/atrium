import { describe, expect, it, vi } from 'vitest'

vi.mock('@/api/rawClient', () => ({
  authenticatedFetch: vi.fn(),
}))

import { duplicatePortalDocument, reorderPortalDocument } from '@/api/documents/documentsApi'
import { authenticatedFetch } from '@/api/rawClient'

describe('documentsApi', () => {
  it('reorderPortalDocument отправляет PATCH с before_id', async () => {
    vi.mocked(authenticatedFetch).mockResolvedValue(
      new Response(JSON.stringify({ id: 'a', title: 'T', body: null }), { status: 200 }),
    )
    await reorderPortalDocument('doc-id', { before_id: 'other-id' })
    expect(authenticatedFetch).toHaveBeenCalledWith(
      '/admin/portal-documents/doc-id/reorder',
      expect.objectContaining({
        method: 'PATCH',
        body: JSON.stringify({ before_id: 'other-id' }),
      }),
    )
  })

  it('duplicatePortalDocument отправляет POST duplicate', async () => {
    vi.mocked(authenticatedFetch).mockResolvedValue(
      new Response(JSON.stringify({ id: 'copy-id' }), { status: 201 }),
    )
    const result = await duplicatePortalDocument('doc-id')
    expect(result).toEqual({ id: 'copy-id' })
    expect(authenticatedFetch).toHaveBeenCalledWith(
      '/admin/portal-documents/doc-id/duplicate',
      expect.objectContaining({ method: 'POST' }),
    )
  })
})
