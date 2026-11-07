import {
  createDocumentComment,
  deleteDocumentComment,
  listDocumentComments,
  updateDocumentComment,
  uploadDocumentCommentMedia,
} from '../../api/documents/documentCommentsApi'
import { useDocumentCommentsThreadWebSocket } from '../../hooks/useCommentThreadWebSocket'
import { documentCommentsQueryKey } from '../../utils/documents/documentNavigation'
import { PortalCommentThread } from '../comments/PortalCommentThread'
import type { ThreadComment } from '../../types/commentThread'

export function DocumentComments({
  documentId,
  currentUserSub,
  resolveUserSub,
  canDeleteAny = false,
  loadPortalUsers = true,
}: {
  documentId: string
  currentUserSub: string
  resolveUserSub: (sub: string) => string
  canDeleteAny?: boolean
  loadPortalUsers?: boolean
}) {
  useDocumentCommentsThreadWebSocket(documentId)
  const qk = documentCommentsQueryKey(documentId)

  return (
    <PortalCommentThread
      queryKey={[...qk]}
      list={async (): Promise<ThreadComment[]> => listDocumentComments(documentId)}
      create={(b) =>
        createDocumentComment(documentId, {
          body: b.body,
          parent_id: b.parent_id ?? undefined,
          mentions: b.mentions,
          media_ids: b.media_ids,
        })
      }
      remove={(id) => deleteDocumentComment(documentId, id)}
      update={(id, body) => updateDocumentComment(documentId, id, body)}
      currentUserSub={currentUserSub}
      resolveUserSub={resolveUserSub}
      enabled={Boolean(documentId)}
      loadPortalUsers={loadPortalUsers}
      canDeleteAny={canDeleteAny}
      uploadImage={(file) => uploadDocumentCommentMedia(documentId, file)}
    />
  )
}
