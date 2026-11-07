import type { DocumentFile } from '../../types/document'
import { parseJsonOrThrowApi } from '../parseResponse'
import { authenticatedFetch } from '../rawClient'

export async function listDocumentFiles(documentId: string): Promise<DocumentFile[]> {
  const res = await authenticatedFetch(`/portal/documents/${encodeURIComponent(documentId)}/files`)
  return parseJsonOrThrowApi(res)
}

export async function uploadDocumentFile(documentId: string, file: File): Promise<DocumentFile> {
  const formData = new FormData()
  formData.append('file', file)
  const res = await authenticatedFetch(`/portal/documents/${encodeURIComponent(documentId)}/files`, {
    method: 'POST',
    body: formData,
  })
  return parseJsonOrThrowApi(res)
}

export async function deleteDocumentFile(documentId: string, fileId: string): Promise<void> {
  const res = await authenticatedFetch(
    `/portal/documents/${encodeURIComponent(documentId)}/files/${encodeURIComponent(fileId)}`,
    { method: 'DELETE' },
  )
  await parseJsonOrThrowApi<void>(res)
}
