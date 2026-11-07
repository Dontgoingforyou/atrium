import { useMutation, useQueryClient, type QueryKey } from '@tanstack/react-query'
import { reorderTask } from '../../api/tasks/tasksApi'
import type { PortalTask, PortalTaskColumn } from '../../types/task'
import { type KanbanInsertAnchor } from '../../domain/kanban/kanbanDisplayCommon'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { useNotifyToast } from '../../hooks/useNotifyToast'
import { shouldPlayTaskDoneSuccess } from '../../domain/tasks/taskColumns'
import { playUiSound } from '../../utils/sound/uiSounds'
import { taskHistoryQueryKey, taskRootQueryKey } from './tasksQueryKeys'

type Options = {
  tasksQueryKey: QueryKey
  columns: PortalTaskColumn[]
  onReorderSuccess: (taskId: string) => void
}

export function useTasksReorderMutation({ tasksQueryKey, columns, onReorderSuccess }: Options) {
  const queryClient = useQueryClient()
  const notifyToast = useNotifyToast()

  return useMutation({
    mutationFn: ({
      taskId,
      newStatus,
      anchor,
    }: {
      taskId: string
      newStatus: string
      anchor: KanbanInsertAnchor
    }) =>
      reorderTask({
        task_id: taskId,
        status: newStatus,
        after_task_id: anchor.afterTaskId,
        before_task_id: anchor.beforeTaskId,
      }),
    onMutate: ({ taskId, newStatus, anchor }) => {
      void queryClient.cancelQueries({ queryKey: tasksQueryKey })
      void queryClient.cancelQueries({ queryKey: taskRootQueryKey(taskId) })
      const previous = queryClient.getQueryData<PortalTask[]>(tasksQueryKey)
      const previousTask = queryClient.getQueryData<PortalTask>(taskRootQueryKey(taskId))
      if (previous) {
        const dragged = previous.find((t) => t.id === taskId)
        if (dragged) {
          const others = previous.filter((t) => t.id !== taskId)
          const inTarget = others
            .filter((t) => t.status === newStatus)
            .sort((a, b) => a.position - b.position)
          let insertAt = inTarget.length
          if (anchor.afterTaskId != null) {
            const idx = inTarget.findIndex((t) => t.id === anchor.afterTaskId)
            insertAt = idx === -1 ? inTarget.length : idx + 1
          } else if (anchor.beforeTaskId != null) {
            const idx = inTarget.findIndex((t) => t.id === anchor.beforeTaskId)
            insertAt = idx === -1 ? 0 : idx
          } else {
            insertAt = 0
          }
          inTarget.splice(insertAt, 0, { ...dragged, status: newStatus })
          const reindexed = inTarget.map((t, i) => ({ ...t, position: i }))
          const reindexedById = new Map(reindexed.map((r) => [r.id, r]))
          const updated = previous.map((t) => reindexedById.get(t.id) ?? t)
          queryClient.setQueryData<PortalTask[]>(tasksQueryKey, updated)
        }
      }
      if (previousTask) {
        queryClient.setQueryData(taskRootQueryKey(taskId), {
          ...previousTask,
          status: newStatus,
        })
      }
      return { previous, previousTask }
    },
    onError: (e: unknown, vars, ctx) => {
      if (ctx?.previous) queryClient.setQueryData(tasksQueryKey, ctx.previous)
      if (ctx?.previousTask) {
        queryClient.setQueryData(taskRootQueryKey(vars.taskId), ctx.previousTask)
      }
      notifyToast(userFacingMessageFromUnknown(e), { tone: 'error' })
    },
    onSuccess: (data, vars, ctx) => {
      const fromStatus = ctx?.previousTask?.status ?? ctx?.previous?.find((t) => t.id === vars.taskId)?.status
      if (fromStatus != null && shouldPlayTaskDoneSuccess(fromStatus, vars.newStatus, columns)) {
        playUiSound('success')
      }
      queryClient.setQueryData(taskRootQueryKey(vars.taskId), data)
      void queryClient.invalidateQueries({ queryKey: tasksQueryKey })
      void queryClient.invalidateQueries({ queryKey: taskHistoryQueryKey(vars.taskId) })
      onReorderSuccess(vars.taskId)
    },
  })
}
