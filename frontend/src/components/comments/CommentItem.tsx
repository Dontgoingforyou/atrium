import { useMemo, useState } from 'react'
import { useMutation, useQueryClient, type QueryKey } from '@tanstack/react-query'

import { isApiConflictError } from '../../api/apiConflict'
import { removeCommentById } from '../../domain/comments/commentThreadTree'
import { useScheduleDeleteWithUndo } from '../../hooks/useScheduleDeleteWithUndo'
import { useNotifyToast } from '../../hooks/useNotifyToast'
import type { PortalUser } from '../../types/chat'
import type {
  CommentThreadUploadResult,
  ThreadComment,
  ThreadCommentCreate,
  ThreadCommentUpdate,
} from '../../types/commentThread'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { MediaLightbox } from '../ui/MediaLightbox'
import { UserChip } from '../ui/UserChip'
import { HighlightedPlainText } from '../search/HighlightedPlainText'
import { renderBodyWithMentionsNodes } from '../tasks/taskCommentsMentionRender'
import { CommentForm } from './CommentForm'
import styles from '@/styles/modules/tasks/TaskComments.module.css'

export function CommentItem({
  comment,
  queryKey,
  remove,
  update,
  currentUserSub,
  resolveUserSub,
  users,
  usersBySub,
  isReply,
  create,
  flat,
  canDeleteAny,
  canCompose,
  highlightQuery,
  uploadImage,
  replyingToId,
  onReplyToggle,
  editingCommentId,
  onEditToggle,
}: {
  comment: ThreadComment
  queryKey: QueryKey
  remove: (id: string) => Promise<void>
  update?: (id: string, body: ThreadCommentUpdate) => Promise<unknown>
  currentUserSub: string
  resolveUserSub: (sub: string) => string
  users: PortalUser[]
  usersBySub: Map<string, PortalUser>
  isReply?: boolean
  create: (b: ThreadCommentCreate) => Promise<unknown>
  flat?: boolean
  canDeleteAny?: boolean
  canCompose?: boolean
  highlightQuery?: string | null
  uploadImage?: (file: File) => Promise<CommentThreadUploadResult>
  replyingToId?: string | null
  onReplyToggle?: (id: string | null) => void
  editingCommentId?: string | null
  onEditToggle?: (id: string | null) => void
}) {
  const queryClient = useQueryClient()
  const scheduleDeleteWithUndo = useScheduleDeleteWithUndo()
  const notifyToast = useNotifyToast()
  const [localReplyOpen, setLocalReplyOpen] = useState(false)
  const showReplyForm = onReplyToggle ? replyingToId === comment.id : localReplyOpen
  const setShowReplyForm = (next: boolean | ((v: boolean) => boolean)) => {
    const open = typeof next === 'function' ? next(showReplyForm) : next
    if (onReplyToggle) {
      onReplyToggle(open ? comment.id : null)
      return
    }
    setLocalReplyOpen(open)
  }
  const [localEditing, setLocalEditing] = useState(false)
  const isEditing = onEditToggle ? editingCommentId === comment.id : localEditing
  const setIsEditing = (next: boolean) => {
    if (onEditToggle) {
      onEditToggle(next ? comment.id : null)
      return
    }
    setLocalEditing(next)
  }
  const [lightboxMedia, setLightboxMedia] = useState<{ url: string; filename: string; contentType: string } | null>(null)

  const deleteMutation = useMutation({
    mutationFn: () => remove(comment.id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey })
    },
    onError: (e: unknown) => notifyToast(userFacingMessageFromUnknown(e)),
  })

  function handleDelete() {
    const previous = queryClient.getQueryData<ThreadComment[]>(queryKey)
    scheduleDeleteWithUndo({
      message: 'Комментарий удалён',
      optimistic: () => {
        queryClient.setQueryData<ThreadComment[]>(queryKey, (prev) =>
          prev ? removeCommentById(prev, comment.id) : prev,
        )
      },
      // Снапшот+restore, а не ручная пересборка дерева — гарантирует, что вложенные
      // ответы вернутся ровно на исходные позиции.
      revert: () => {
        if (previous !== undefined) {
          queryClient.setQueryData(queryKey, previous)
        }
      },
      commit: () => deleteMutation.mutate(),
    })
  }

  const canDelete = comment.author_sub === currentUserSub || Boolean(canDeleteAny)
  const canEdit = Boolean(update) && (comment.author_sub === currentUserSub || Boolean(canDeleteAny))
  const authorLabel =
    comment.author_display_name?.trim() || resolveUserSub(comment.author_sub)
  const author = usersBySub.get(comment.author_sub)
  const isEdited = comment.updated_at !== comment.created_at

  const bodyNodes = useMemo(
    () => renderBodyWithMentionsNodes(comment.body, comment.mentions, users),
    [comment.body, comment.mentions, users],
  )

  return (
    <li
      className={`${styles.comment} ${flat ? styles.commentFlat : ''} ${isReply ? styles.reply : ''}`}
    >
      <div className={`${styles.commentMeta} ${flat ? styles.commentMetaDocument : ''}`}>
        <UserChip
          label={authorLabel}
          imageUrl={author?.avatar_url}
          focalX={author?.avatar_focal_x}
          focalY={author?.avatar_focal_y}
          size="sm"
          className={styles.commentAuthor}
        />
        <span className={styles.commentDate}>
          {new Date(comment.created_at).toLocaleString('ru-RU')}
          {isEdited ? ' (ред.)' : ''}
        </span>
      </div>
      {isEditing && update ? (
        <CommentForm
          queryKey={queryKey}
          update={async (body) => {
            try {
              return await update(comment.id, {
                ...body,
                expected_version: comment.version,
              })
            } catch (e: unknown) {
              if (isApiConflictError(e)) {
                void queryClient.invalidateQueries({ queryKey })
              }
              throw e
            }
          }}
          users={users}
          initialBody={comment.body}
          initialMentions={comment.mentions}
          placeholder="Изменить комментарий…"
          onSuccess={() => setIsEditing(false)}
          onCancel={() => setIsEditing(false)}
          autoFocus
        />
      ) : (
        <>
          <p className={styles.commentBody}>
            {highlightQuery && comment.mentions.length === 0 ? (
              <HighlightedPlainText text={comment.body} query={highlightQuery} />
            ) : (
              bodyNodes
            )}
          </p>
          {comment.media && comment.media.length > 0 && (
            <div className={styles.commentMediaGrid}>
              {comment.media.map((m) => (
                <button
                  key={m.id}
                  type="button"
                  className={styles.commentMediaItem}
                  title={m.original_filename}
                  aria-label={`Открыть вложение ${m.original_filename}`}
                  onClick={() => setLightboxMedia({ url: m.download_url, filename: m.original_filename, contentType: m.content_type })}
                >
                  <img src={m.download_url} alt={m.original_filename} className={styles.commentMediaImg} />
                </button>
              ))}
            </div>
          )}
          {lightboxMedia && (
            <MediaLightbox
              url={lightboxMedia.url}
              filename={lightboxMedia.filename}
              contentType={lightboxMedia.contentType}
              onClose={() => setLightboxMedia(null)}
            />
          )}
          <div className={styles.commentActions}>
            {canCompose !== false && (
              <button
                type="button"
                className={styles.actionBtn}
                onClick={() => {
                  setShowReplyForm((v) => !v)
                  setIsEditing(false)
                }}
              >
                {showReplyForm ? 'Отмена' : 'Ответить'}
              </button>
            )}
            {canEdit && (
              <button
                type="button"
                className={styles.actionBtn}
                onClick={() => {
                  setIsEditing(true)
                  setShowReplyForm(false)
                }}
              >
                Редактировать
              </button>
            )}
            {canDelete && (
              <button type="button" className={styles.deleteBtn} onClick={handleDelete}>
                Удалить
              </button>
            )}
          </div>
        </>
      )}
      {canCompose !== false && showReplyForm && !isEditing && (
        <CommentForm
          queryKey={queryKey}
          create={create}
          parentId={comment.id}
          users={users}
          placeholder="Ответить на комментарий…"
          onSuccess={() => setShowReplyForm(false)}
          onCancel={() => setShowReplyForm(false)}
          autoFocus
          uploadImage={uploadImage}
        />
      )}
      {comment.replies.length > 0 && (
        <ul className={styles.repliesList}>
          {comment.replies.map((reply) => (
            <CommentItem
              key={reply.id}
              comment={reply}
              queryKey={queryKey}
              remove={remove}
              update={update}
              currentUserSub={currentUserSub}
              resolveUserSub={resolveUserSub}
              users={users}
              usersBySub={usersBySub}
              create={create}
              isReply
              flat={flat}
              canDeleteAny={canDeleteAny}
              canCompose={canCompose}
              highlightQuery={highlightQuery}
              uploadImage={uploadImage}
              replyingToId={replyingToId}
              onReplyToggle={onReplyToggle}
              editingCommentId={editingCommentId}
              onEditToggle={onEditToggle}
            />
          ))}
        </ul>
      )}
    </li>
  )
}
