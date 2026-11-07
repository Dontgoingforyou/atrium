import { createComment, deleteComment, listComments, updateComment, uploadTaskCommentMedia } from '../../../api/tasks/tasksApi'
import { useTaskCommentsThreadWebSocket } from '../../../hooks/useCommentThreadWebSocket'
import { taskCommentsQueryKey } from '@/pages/tasks/tasksQueryKeys'
import { PortalCommentThread } from '../../comments/PortalCommentThread'
import type { ThreadComment } from '../../../types/commentThread'

export function TaskComments({
  taskId,
  currentUserSub,
  resolveUserSub,
}: {
  taskId: string
  currentUserSub: string
  resolveUserSub: (sub: string) => string
}) {
  useTaskCommentsThreadWebSocket(taskId)
  const qk = taskCommentsQueryKey(taskId)

  async function fromApi(): Promise<ThreadComment[]> {
    return listComments(taskId)
  }

  return (
    <PortalCommentThread
      queryKey={[...qk]}
      list={fromApi}
      create={(b) =>
        createComment(taskId, {
          body: b.body,
          parent_id: b.parent_id ?? undefined,
          mentions: b.mentions,
          media_ids: b.media_ids,
        })
      }
      remove={(id) => deleteComment(taskId, id)}
      update={(id, body) => updateComment(taskId, id, body)}
      currentUserSub={currentUserSub}
      resolveUserSub={resolveUserSub}
      enabled={Boolean(taskId)}
      uploadImage={(file) => uploadTaskCommentMedia(taskId, file)}
    />
  )
}
