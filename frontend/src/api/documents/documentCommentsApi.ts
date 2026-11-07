import { createCommentThreadApi } from '../commentThreadApi'
import type { RichMediaRead } from '../richMediaApi'
import type { ThreadComment, ThreadCommentUpdate } from '../../types/commentThread'

function apiForDocument(documentId: string) {
  return createCommentThreadApi(
    `/portal/documents/${encodeURIComponent(documentId)}/comments`,
  )
}

export async function listDocumentComments(documentId: string): Promise<ThreadComment[]> {
  return apiForDocument(documentId).list()
}

export async function createDocumentComment(
  documentId: string,
  body: { body: string; parent_id?: string | null; mentions?: string[]; media_ids?: string[] },
): Promise<ThreadComment> {
  return apiForDocument(documentId).create({
    body: body.body,
    parent_id: body.parent_id ?? null,
    mentions: body.mentions ?? [],
    media_ids: body.media_ids,
  })
}

export async function deleteDocumentComment(documentId: string, commentId: string): Promise<void> {
  await apiForDocument(documentId).remove(commentId)
}

export async function updateDocumentComment(
  documentId: string,
  commentId: string,
  body: ThreadCommentUpdate,
): Promise<ThreadComment> {
  return apiForDocument(documentId).update(commentId, body)
}

export async function uploadDocumentCommentMedia(documentId: string, file: File): Promise<RichMediaRead> {
  return apiForDocument(documentId).uploadMedia(file)
}
