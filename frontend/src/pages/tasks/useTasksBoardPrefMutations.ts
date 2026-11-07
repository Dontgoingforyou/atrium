import { useCallback, useRef } from 'react'
import { useMutation, useQueryClient, type QueryKey } from '@tanstack/react-query'
import { putTaskBoardPref } from '../../api/tasks/tasksApi'
import type { TaskBoardPref, TaskBoardPrefWrite } from '../../types/task'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { useNotifyToast } from '../../hooks/useNotifyToast'

type Options = {
  boardPrefQueryKey: QueryKey
  boardPref: TaskBoardPref | undefined
}

function emptyPref(): TaskBoardPref {
  return {
    column_order: [],
    hidden_status_keys: [],
    title_overrides: {},
    subtasks_flat: false,
    hide_subtasks: false,
  }
}

export function useTasksBoardPrefMutations({ boardPrefQueryKey, boardPref }: Options) {
  const queryClient = useQueryClient()
  const notifyToast = useNotifyToast()
  const columnReorderTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const putBoardPrefMutation = useMutation({
    mutationFn: (body: TaskBoardPrefWrite) => putTaskBoardPref(body),
    onMutate: async (body) => {
      await queryClient.cancelQueries({ queryKey: boardPrefQueryKey })
      const previous = queryClient.getQueryData<TaskBoardPref>(boardPrefQueryKey)
      if (previous) {
        queryClient.setQueryData<TaskBoardPref>(boardPrefQueryKey, {
          ...previous,
          column_order: body.column_order ?? previous.column_order,
          hidden_status_keys: body.hidden_status_keys ?? previous.hidden_status_keys,
          title_overrides: body.title_overrides ?? previous.title_overrides,
          subtasks_flat: body.subtasks_flat ?? previous.subtasks_flat,
          hide_subtasks: body.hide_subtasks ?? previous.hide_subtasks,
        })
      }
      return { previous }
    },
    onSuccess: (data) => {
      queryClient.setQueryData<TaskBoardPref>(boardPrefQueryKey, data)
    },
    onError: (e: unknown, _body, ctx) => {
      if (ctx?.previous) queryClient.setQueryData(boardPrefQueryKey, ctx.previous)
      notifyToast(userFacingMessageFromUnknown(e))
    },
  })

  function currentBoardPrefPayload(): TaskBoardPrefWrite {
    const cur = queryClient.getQueryData<TaskBoardPref>(boardPrefQueryKey) ?? emptyPref()
    return {
      column_order: [...cur.column_order],
      hidden_status_keys: [...cur.hidden_status_keys],
      title_overrides: { ...cur.title_overrides },
      subtasks_flat: cur.subtasks_flat ?? false,
      hide_subtasks: cur.hide_subtasks ?? false,
    }
  }

  function handlePersonalColumnReorder(newStatusOrder: string[]) {
    const base = currentBoardPrefPayload()
    queryClient.setQueryData<TaskBoardPref>(boardPrefQueryKey, (prev) =>
      prev
        ? { ...prev, column_order: newStatusOrder }
        : { ...emptyPref(), column_order: newStatusOrder },
    )
    if (columnReorderTimerRef.current) clearTimeout(columnReorderTimerRef.current)
    columnReorderTimerRef.current = setTimeout(() => {
      putBoardPrefMutation.mutate({
        ...base,
        column_order: newStatusOrder,
      })
    }, 300)
  }

  function toggleHiddenColumn(statusKey: string) {
    const base = currentBoardPrefPayload()
    const hidden = new Set(base.hidden_status_keys)
    if (hidden.has(statusKey)) hidden.delete(statusKey)
    else hidden.add(statusKey)
    putBoardPrefMutation.mutate({ ...base, hidden_status_keys: [...hidden] })
  }

  function toggleSubtasksFlat() {
    const base = currentBoardPrefPayload()
    const next = !(boardPref?.subtasks_flat ?? false)
    putBoardPrefMutation.mutate({
      ...base,
      subtasks_flat: next,
      hide_subtasks: next ? false : base.hide_subtasks,
    })
  }

  function toggleHideSubtasks() {
    const base = currentBoardPrefPayload()
    const next = !(boardPref?.hide_subtasks ?? false)
    putBoardPrefMutation.mutate({
      ...base,
      hide_subtasks: next,
      subtasks_flat: next ? false : base.subtasks_flat,
    })
  }

  const clearColumnReorderTimer = useCallback(() => {
    if (columnReorderTimerRef.current) clearTimeout(columnReorderTimerRef.current)
  }, [])

  return {
    putBoardPrefMutation,
    handlePersonalColumnReorder,
    toggleHiddenColumn,
    toggleSubtasksFlat,
    toggleHideSubtasks,
    clearColumnReorderTimer,
  }
}
