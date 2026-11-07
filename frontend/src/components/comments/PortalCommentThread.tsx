import { useMemo, useRef, useState, type ReactNode } from 'react'
import { useQuery, type QueryKey } from '@tanstack/react-query'

import { portalUsersQueryOptions } from '../../api/queryKeys'
import type { PortalUser } from '../../types/chat'
import type {
  CommentThreadUploadResult,
  ThreadComment,
  ThreadCommentCreate,
  ThreadCommentUpdate,
} from '../../types/commentThread'
import { useScrollToSearchHit } from '../../hooks/useScrollToSearchHit'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { CommentForm } from './CommentForm'
import { CommentItem } from './CommentItem'
import styles from '@/styles/modules/tasks/TaskComments.module.css'

const EMPTY_PORTAL_USERS: PortalUser[] = []

type Props = {
  queryKey: QueryKey
  list: () => Promise<ThreadComment[]>
  create: (b: ThreadCommentCreate) => Promise<unknown>
  remove: (id: string) => Promise<void>
  update?: (id: string, body: ThreadCommentUpdate) => Promise<unknown>
  currentUserSub: string
  resolveUserSub: (sub: string) => string
  enabled?: boolean
  /** Загрузка /portal/users для имён и @упоминаний (у timesheet-only недоступна). */
  loadPortalUsers?: boolean
  canDeleteAny?: boolean
  /** false — без ответа и нижнего поля. */
  canCompose?: boolean
  highlightQuery?: string | null
  uploadImage?: (file: File) => Promise<CommentThreadUploadResult>
}

export function PortalCommentThread({
  queryKey,
  list,
  create,
  remove,
  update,
  currentUserSub,
  resolveUserSub,
  enabled = true,
  loadPortalUsers = true,
  canDeleteAny = false,
  canCompose = true,
  highlightQuery = null,
  uploadImage,
}: Props) {
  const rootRef = useRef<HTMLDivElement>(null)
  const [replyingToId, setReplyingToId] = useState<string | null>(null)
  const [editingCommentId, setEditingCommentId] = useState<string | null>(null)
  const commentsQuery = useQuery({
    queryKey,
    queryFn: list,
    enabled: Boolean(enabled),
  })

  const usersQuery = useQuery({
    ...portalUsersQueryOptions(500),
    enabled: Boolean(enabled) && loadPortalUsers,
  })

  const users = usersQuery.data ?? EMPTY_PORTAL_USERS
  const usersError = loadPortalUsers ? usersQuery.isError : false
  const usersErrorData = usersQuery.error
  const usersBySub = useMemo(() => {
    const map = new Map<string, PortalUser>()
    for (const u of users) map.set(u.sub, u)
    return map
  }, [users])
  const comments = commentsQuery.data ?? []
  useScrollToSearchHit(rootRef, highlightQuery, !commentsQuery.isPending && comments.length > 0)

  let body: ReactNode
  if (commentsQuery.isPending) {
    body = <p className="text-muted">Загрузка комментариев…</p>
  } else if (commentsQuery.isError) {
    body = <p className="text-danger">{userFacingMessageFromUnknown(commentsQuery.error)}</p>
  } else {
    const showForm = !replyingToId && !editingCommentId
    body = (
      <>
        {comments.length === 0 ? (
          <p className="text-muted">Комментариев пока нет.</p>
        ) : (
          <ul className={styles.commentsList}>
            {comments.map((c) => (
              <CommentItem
                key={c.id}
                comment={c}
                queryKey={queryKey}
                remove={remove}
                update={update}
                currentUserSub={currentUserSub}
                resolveUserSub={resolveUserSub}
                users={users}
                usersBySub={usersBySub}
                create={create}
                canDeleteAny={canDeleteAny}
                canCompose={canCompose}
                highlightQuery={highlightQuery}
                uploadImage={uploadImage}
                replyingToId={replyingToId}
                onReplyToggle={setReplyingToId}
                editingCommentId={editingCommentId}
                onEditToggle={setEditingCommentId}
              />
            ))}
          </ul>
        )}
        {showForm && canCompose ? (
          <CommentForm
            queryKey={queryKey}
            create={create}
            users={users}
            mentionsUnavailable={Boolean(usersError)}
            onSuccess={() => undefined}
            uploadImage={uploadImage}
          />
        ) : null}
        {usersError ? (
          <p className="text-muted" role="status">
            Упоминания недоступны: {userFacingMessageFromUnknown(usersErrorData)}
          </p>
        ) : null}
      </>
    )
  }

  return (
    <div className={styles.root} ref={rootRef}>
      {body}
    </div>
  )
}
