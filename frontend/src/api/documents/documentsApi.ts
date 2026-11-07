import type { PagedResponse } from '../../types/timeEntry'
import type {
  PortalDocument,
  PortalDocumentBrief,
  PortalDocumentCreate,
  PortalDocumentHistory,
  PortalDocumentQuickCreate,
  PortalDocumentReorderRequest,
  PortalDocumentTrashItem,
  PortalDocumentUpdate,
} from '../../types/document'
import { parseJsonOrThrowApi } from '../parseResponse'
import { authenticatedFetch } from '../rawClient'

export async function listDocuments(params?: {
  tag_slug?: string
  skip?: number
  limit?: number
}): Promise<PagedResponse<PortalDocumentBrief>> {
  const qs = new URLSearchParams()
  if (params?.tag_slug) qs.set('tag_slug', params.tag_slug)
  if (params?.skip !== undefined) qs.set('skip', String(params.skip))
  if (params?.limit !== undefined) qs.set('limit', String(params.limit))
  const query = qs.toString() ? `?${qs}` : ''
  const res = await authenticatedFetch(`/portal/documents${query}`)
  return parseJsonOrThrowApi(res)
}

export async function getDocument(documentId: string): Promise<PortalDocument> {
  const res = await authenticatedFetch(`/portal/documents/${documentId}`)
  return parseJsonOrThrowApi(res)
}

export async function getDocumentHistory(documentId: string): Promise<PortalDocumentHistory[]> {
  const res = await authenticatedFetch(`/portal/documents/${documentId}/history`)
  return parseJsonOrThrowApi(res)
}

export async function listChildDocuments(parentDocumentId: string): Promise<PortalDocumentBrief[]> {
  const res = await authenticatedFetch(
    `/portal/documents/${encodeURIComponent(parentDocumentId)}/children`,
  )
  return parseJsonOrThrowApi(res)
}

export async function quickCreateDocument(body: PortalDocumentQuickCreate): Promise<{ id: string }> {
  const res = await authenticatedFetch('/admin/portal-documents/quick-create', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi(res)
}

export async function createPortalDocument(body: PortalDocumentCreate): Promise<PortalDocument> {
  const res = await authenticatedFetch('/admin/portal-documents', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi(res)
}

export async function updatePortalDocument(
  documentId: string,
  body: PortalDocumentUpdate,
): Promise<PortalDocument> {
  const res = await authenticatedFetch(
    `/admin/portal-documents/${encodeURIComponent(documentId)}`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
  )
  return parseJsonOrThrowApi(res)
}

export async function patchPortalDocumentWithCas(
  documentId: string,
  patch: Omit<PortalDocumentUpdate, 'expected_version'>,
  expectedVersion?: number,
): Promise<PortalDocument> {
  const version = expectedVersion ?? (await getDocument(documentId)).version
  return updatePortalDocument(documentId, { ...patch, expected_version: version })
}

export async function deletePortalDocument(documentId: string): Promise<void> {
  const res = await authenticatedFetch(
    `/admin/portal-documents/${encodeURIComponent(documentId)}`,
    { method: 'DELETE' },
  )
  await parseJsonOrThrowApi(res)
}

export async function listTrashDocuments(params?: {
  skip?: number
  limit?: number
}): Promise<PagedResponse<PortalDocumentTrashItem>> {
  const qs = new URLSearchParams()
  if (params?.skip !== undefined) qs.set('skip', String(params.skip))
  if (params?.limit !== undefined) qs.set('limit', String(params.limit))
  const query = qs.toString() ? `?${qs}` : ''
  const res = await authenticatedFetch(`/admin/portal-documents/trash${query}`)
  return parseJsonOrThrowApi(res)
}

export async function restorePortalDocument(documentId: string): Promise<PortalDocument> {
  const res = await authenticatedFetch(
    `/admin/portal-documents/${encodeURIComponent(documentId)}/restore`,
    { method: 'POST' },
  )
  return parseJsonOrThrowApi(res)
}

export async function purgePortalDocument(documentId: string): Promise<void> {
  const res = await authenticatedFetch(
    `/admin/portal-documents/${encodeURIComponent(documentId)}/purge`,
    { method: 'DELETE' },
  )
  await parseJsonOrThrowApi(res)
}

export async function reorderPortalDocument(
  documentId: string,
  body: PortalDocumentReorderRequest,
): Promise<PortalDocument> {
  const res = await authenticatedFetch(
    `/admin/portal-documents/${encodeURIComponent(documentId)}/reorder`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
  )
  return parseJsonOrThrowApi(res)
}

export async function duplicatePortalDocument(documentId: string): Promise<{ id: string }> {
  const res = await authenticatedFetch(
    `/admin/portal-documents/${encodeURIComponent(documentId)}/duplicate`,
    { method: 'POST' },
  )
  return parseJsonOrThrowApi(res)
}
