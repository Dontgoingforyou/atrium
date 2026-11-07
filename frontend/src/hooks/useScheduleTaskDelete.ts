import { useCallback } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'

import { deleteTask } from '../api/tasks/tasksApi'
import { PORTAL_TASKS_ROOT_QUERY_KEY } from '../api/queryKeys'
import { taskRootQueryKey } from '../pages/tasks/tasksQueryKeys'
import { userFacingMessageFromUnknown } from '../utils/apiUserMessage'
import { invalidatePortalSearchQueries } from '@/utils/search/invalidatePortalSearch'
import { playUiSound } from '../utils/sound/uiSounds'
import { useNotifyToast } from './useNotifyToast'
import { useDelayedActionContext } from './useDelayedActionContext'

type ScheduleTaskDeleteArgs = {
  taskId: string
  /** Точечный optimistic-патч кэша списка задач вызывающей страницы (например tasksQueryKey канбана). */
  patchListCache?: () => void
  /** Восстановление того же кэша при отмене — до commit. */
  revertListCache?: () => void
}

export function useScheduleTaskDelete() {
  const queryClient = useQueryClient()
  const notifyToast = useNotifyToast()
  const { hideOptimistically, showOptimistically, schedule } = useDelayedActionContext()

  const deleteMutation = useMutation({
    mutationFn: (taskId: string) => deleteTask(taskId),
    onSuccess: (_data, taskId) => {
      void queryClient.invalidateQueries({ queryKey: PORTAL_TASKS_ROOT_QUERY_KEY })
      void queryClient.removeQueries({ queryKey: taskRootQueryKey(taskId) })
      invalidatePortalSearchQueries(queryClient)
    },
    onError: (e: unknown) => notifyToast(userFacingMessageFromUnknown(e), { tone: 'error' }),
  })

  const scheduleTaskDelete = useCallback(
    ({ taskId, patchListCache, revertListCache }: ScheduleTaskDeleteArgs) => {
      playUiSound('error')
      hideOptimistically(taskId)
      patchListCache?.()
      schedule({
        message: 'Задача удалена',
        onCommit: () => {
          deleteMutation.mutate(taskId, { onSettled: () => showOptimistically(taskId) })
        },
        onRevert: () => {
          showOptimistically(taskId)
          revertListCache?.()
        },
        onUndoClick: () => showOptimistically(taskId),
      })
    },
    [deleteMutation, hideOptimistically, schedule, showOptimistically],
  )

  return { scheduleTaskDelete, deleteMutation }
}
