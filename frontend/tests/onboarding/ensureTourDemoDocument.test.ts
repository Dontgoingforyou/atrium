import { describe, expect, it, vi, beforeEach } from 'vitest'

import {
  cleanupGuidedTourDemoDocument,
  ensureGuidedTourDemoDocument,
  stepNeedsTourDemoDocument,
  TOUR_DEMO_DOCUMENT_TITLE,
} from '../../src/onboarding/ensureTourDemoDocument'

vi.mock('../../src/api/rawClient', () => ({
  authenticatedFetch: vi.fn(),
}))

import { authenticatedFetch } from '../../src/api/rawClient'

function res(body: string, ok = true) {
  return {
    ok,
    status: ok ? 200 : 500,
    text: async () => body,
  } as unknown as Response
}

describe('ensureGuidedTourDemoDocument', () => {
  beforeEach(() => {
    vi.mocked(authenticatedFetch).mockReset()
  })

  it('returns created document when ensure creates a new one', async () => {
    vi.mocked(authenticatedFetch).mockResolvedValue(res(JSON.stringify({ id: 'doc1', created: true })))
    const result = await ensureGuidedTourDemoDocument()
    expect(result).toEqual({ ok: true, created: true, documentId: 'doc1' })
    expect(authenticatedFetch).toHaveBeenCalledWith('/portal/documents/tour-demo/ensure', {
      method: 'POST',
    })
  })

  it('returns reused document when ensure finds existing', async () => {
    vi.mocked(authenticatedFetch).mockResolvedValue(res(JSON.stringify({ id: 'doc2', created: false })))
    const result = await ensureGuidedTourDemoDocument()
    expect(result).toEqual({ ok: true, created: false, documentId: 'doc2' })
  })

  it('fails when response has no id', async () => {
    vi.mocked(authenticatedFetch).mockResolvedValue(res(JSON.stringify({ created: true })))
    const result = await ensureGuidedTourDemoDocument()
    expect(result.ok).toBe(false)
  })

  it('fails when fetch throws', async () => {
    vi.mocked(authenticatedFetch).mockRejectedValue(new Error('network'))
    const result = await ensureGuidedTourDemoDocument()
    expect(result.ok).toBe(false)
  })

  it('fails when HTTP !ok', async () => {
    vi.mocked(authenticatedFetch).mockResolvedValue(res('{"detail":"nope"}', false))
    const result = await ensureGuidedTourDemoDocument()
    expect(result.ok).toBe(false)
  })

  it('cleanup sends DELETE and swallows errors', async () => {
    vi.mocked(authenticatedFetch).mockRejectedValueOnce(new Error('gone'))
    await expect(cleanupGuidedTourDemoDocument()).resolves.toBeUndefined()
    expect(authenticatedFetch).toHaveBeenCalledWith('/portal/documents/tour-demo', {
      method: 'DELETE',
    })
  })

  it('exposes tour demo document title', () => {
    expect(TOUR_DEMO_DOCUMENT_TITLE).toBe('Учебный документ')
  })

  it('stepNeedsTourDemoDocument detects document steps', () => {
    expect(stepNeedsTourDemoDocument({ id: 'nav-documents' })).toBe(true)
    expect(stepNeedsTourDemoDocument({ id: 'document-title' })).toBe(true)
    expect(stepNeedsTourDemoDocument({ id: 'document-body' })).toBe(true)
    expect(stepNeedsTourDemoDocument({ id: 'document-comments' })).toBe(true)
    expect(stepNeedsTourDemoDocument({ id: 'document-tags' })).toBe(false)
  })
})
