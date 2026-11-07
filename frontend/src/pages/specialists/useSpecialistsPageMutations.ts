import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { QueryKey } from '@tanstack/react-query'

import { isApiConflictError } from '../../api/apiConflict'
import {
  createSpecialistColumn,
  deleteSpecialistColumn,
  moveOnBoardApi,
  putSpecialistBoardPref,
  reorderOnBoardApi,
  updateSpecialistColumn,
} from '../../api/specialists/specialistsApi'
import { mergeSpecialistColumnOrder } from '../../domain/specialists/specialistBoardPref'
import type { KanbanInsertAnchor } from '../../domain/kanban/kanbanDisplayCommon'
import { QK_BOARD_ROOT, QK_COLUMNS, QK_PREF } from '../../domain/specialists/specialistBoardCache'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { useNotifyToast } from '../../hooks/useNotifyToast'
import { useScheduleDeleteWithUndo } from '../../hooks/useScheduleDeleteWithUndo'
import type {
  ManagerSpecialistEntry,
  SpecialistBoardPref,
  SpecialistBoardPrefWrite,
  SpecialistColumn,
} from '../../types/specialist'

const QK_BOARD = QK_BOARD_ROOT

interface Props {
  columns: SpecialistColumn[]
  boardQueryKey: QueryKey
}

/** Мутации страницы специалистов: перемещение/reorder карточек, колонки, личные настройки доски. */
export function useSpecialistsPageMutations({ columns, boardQueryKey }: Props) {
  const queryClient = useQueryClient()
  const notifyToast = useNotifyToast()
  const scheduleDeleteWithUndo = useScheduleDeleteWithUndo()

  function boardParams(managerSub?: string) {
    return managerSub ? { manager_sub: managerSub } : undefined
  }

  function invalidateBoard() {
    void queryClient.invalidateQueries({ queryKey: QK_BOARD })
  }

  const prefMutation = useMutation({
    mutationFn: putSpecialistBoardPref,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: QK_PREF }),
    onError: (e: unknown) => notifyToast(userFacingMessageFromUnknown(e)),
  })

  function currentBoardPrefPayload(): SpecialistBoardPrefWrite {
    const cur =
      queryClient.getQueryData<SpecialistBoardPref>(QK_PREF) ??
      ({ column_order: [], hidden_column_keys: [] } satisfies SpecialistBoardPref)
    const knownKeys = new Set(columns.map((c) => c.key))
    return {
      column_order: mergeSpecialistColumnOrder(columns, cur),
      hidden_column_keys: cur.hidden_column_keys.filter((k) => knownKeys.has(k)),
    }
  }

  function handlePersonalColumnReorder(newOrder: string[]) {
    prefMutation.mutate({ ...currentBoardPrefPayload(), column_order: newOrder })
  }

  function toggleHiddenColumn(columnKey: string) {
    const base = currentBoardPrefPayload()
    const hidden = new Set(base.hidden_column_keys)
    if (hidden.has(columnKey)) hidden.delete(columnKey)
    else hidden.add(columnKey)
    prefMutation.mutate({ ...base, hidden_column_keys: [...hidden] })
  }

  const moveMutation = useMutation({
    mutationFn: ({
      specialistSub,
      columnKey,
      managerSub,
    }: {
      specialistSub: string
      columnKey: string
      managerSub?: string
    }) => {
      const cached =
        queryClient.getQueryData<ManagerSpecialistEntry[]>(boardQueryKey) ??
        queryClient.getQueryData<ManagerSpecialistEntry[]>(QK_BOARD) ??
        []
      const entry = cached.find((e) => {
        if (e.specialist_sub !== specialistSub) return false
        if (managerSub) return e.manager_sub === managerSub
        return true
      })
      if (entry == null) {
        throw new Error('Запись специалиста на доске не найдена в кэше')
      }
      return moveOnBoardApi(
        specialistSub,
        { column_key: columnKey, expected_version: entry.version },
        boardParams(managerSub),
      )
    },
    onSettled: invalidateBoard,
    onError: (e: unknown) => {
      notifyToast(userFacingMessageFromUnknown(e))
      if (isApiConflictError(e)) {
        invalidateBoard()
      }
    },
  })

  const reorderMutation = useMutation({
    mutationFn: ({
      entryId,
      columnKey,
      anchor,
      managerSub,
    }: {
      entryId: string
      columnKey: string
      anchor: KanbanInsertAnchor
      managerSub?: string
    }) =>
      reorderOnBoardApi(
        {
          entry_id: entryId,
          column_key: columnKey,
          after_entry_id: anchor.afterTaskId,
          before_entry_id: anchor.beforeTaskId,
        },
        boardParams(managerSub),
      ),
    onMutate: ({ entryId, columnKey, anchor }) => {
      const previous = queryClient.getQueryData<ManagerSpecialistEntry[]>(boardQueryKey)
      if (!previous) return { previous }
      const moving = previous.find((entry) => entry.id === entryId)
      if (!moving) return { previous }
      const target = previous
        .filter((entry) => entry.id !== entryId && entry.column_key === columnKey)
        .sort((a, b) => a.position - b.position)
      let insertAt = 0
      if (anchor.afterTaskId !== null) {
        const idx = target.findIndex((entry) => entry.id === anchor.afterTaskId)
        insertAt = idx < 0 ? target.length : idx + 1
      } else if (anchor.beforeTaskId !== null) {
        const idx = target.findIndex((entry) => entry.id === anchor.beforeTaskId)
        insertAt = idx < 0 ? 0 : idx
      }
      target.splice(insertAt, 0, { ...moving, column_key: columnKey })
      const byId = new Map(target.map((entry, position) => [entry.id, { ...entry, position }]))
      queryClient.setQueryData<ManagerSpecialistEntry[]>(
        boardQueryKey,
        previous.map((entry) => byId.get(entry.id) ?? entry),
      )
      return { previous }
    },
    onError: (error: unknown, _vars, context) => {
      if (context?.previous) queryClient.setQueryData(boardQueryKey, context.previous)
      notifyToast(userFacingMessageFromUnknown(error))
    },
    onSettled: invalidateBoard,
  })

  const addColumnMutation = useMutation({
    mutationFn: (data: { key: string; title: string; color: string; position: number }) =>
      createSpecialistColumn(data),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: QK_COLUMNS }),
    onError: (e: unknown) => notifyToast(userFacingMessageFromUnknown(e)),
  })

  const updateColumnMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: { title?: string; color?: string } }) =>
      updateSpecialistColumn(id, data),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: QK_COLUMNS }),
    onError: (e: unknown) => notifyToast(userFacingMessageFromUnknown(e)),
  })

  const deleteColumnMutation = useMutation({
    mutationFn: (id: string) => deleteSpecialistColumn(id),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: QK_COLUMNS }),
    onError: (e: unknown) => notifyToast(userFacingMessageFromUnknown(e)),
  })

  function scheduleSpecialistColumnDelete(columnId: string) {
    const previous = queryClient.getQueryData<SpecialistColumn[]>(QK_COLUMNS)
    scheduleDeleteWithUndo({
      message: 'Колонка удалена',
      optimistic: () => {
        queryClient.setQueryData<SpecialistColumn[]>(QK_COLUMNS, (prev) =>
          prev ? prev.filter((c) => c.id !== columnId) : [],
        )
      },
      revert: () => {
        if (previous) queryClient.setQueryData(QK_COLUMNS, previous)
      },
      commit: () => deleteColumnMutation.mutate(columnId),
    })
  }

  return {
    prefMutation,
    moveMutation,
    reorderMutation,
    addColumnMutation,
    updateColumnMutation,
    deleteColumnMutation,
    scheduleSpecialistColumnDelete,
    handlePersonalColumnReorder,
    toggleHiddenColumn,
  }
}
