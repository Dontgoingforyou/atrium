import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createTaskColumn, deleteTaskColumn, updateTaskColumn } from '../../api/tasks/tasksApi'
import { PORTAL_HOME_QUERY_KEY, PORTAL_TASK_COLUMNS_QUERY_KEY } from '../../api/queryKeys'
import { useNotifyToast } from '../../hooks/useNotifyToast'
import { useScheduleDeleteWithUndo } from '../../hooks/useScheduleDeleteWithUndo'
import type { PortalTaskColumn, TaskColumnCreate, TaskColumnUpdate } from '../../types/task'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'

const taskColumnsQueryKey = PORTAL_TASK_COLUMNS_QUERY_KEY

export function useTasksColumnMutations() {
  const queryClient = useQueryClient()
  const notifyToast = useNotifyToast()
  const scheduleDeleteWithUndo = useScheduleDeleteWithUndo()

  const updateColumnMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: TaskColumnUpdate }) => updateTaskColumn(id, data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: taskColumnsQueryKey })
      void queryClient.invalidateQueries({ queryKey: PORTAL_HOME_QUERY_KEY })
    },
    onError: (e: unknown) => notifyToast(userFacingMessageFromUnknown(e)),
  })

  const createColumnMutation = useMutation({
    mutationFn: (data: TaskColumnCreate) => createTaskColumn(data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: taskColumnsQueryKey }),
    onError: (e: unknown) => notifyToast(userFacingMessageFromUnknown(e)),
  })

  const deleteColumnMutation = useMutation({
    mutationFn: (id: string) => deleteTaskColumn(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: taskColumnsQueryKey }),
    onError: (e: unknown) => notifyToast(userFacingMessageFromUnknown(e), { tone: 'error' }),
  })

  function scheduleTaskColumnDelete(columnId: string) {
    const previous = queryClient.getQueryData<PortalTaskColumn[]>(taskColumnsQueryKey)
    scheduleDeleteWithUndo({
      message: 'Колонка удалена',
      optimistic: () => {
        queryClient.setQueryData<PortalTaskColumn[]>(taskColumnsQueryKey, (prev) =>
          prev ? prev.filter((c) => c.id !== columnId) : [],
        )
      },
      revert: () => {
        if (previous) queryClient.setQueryData(taskColumnsQueryKey, previous)
      },
      commit: () => deleteColumnMutation.mutate(columnId),
    })
  }

  return {
    updateColumnMutation,
    createColumnMutation,
    deleteColumnMutation,
    scheduleTaskColumnDelete,
  }
}
