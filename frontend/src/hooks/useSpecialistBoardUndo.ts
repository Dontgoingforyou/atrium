import { useCallback, useMemo } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'

import { isApiConflictError } from '../api/apiConflict'
import { addToBoardApi, listBoardEntries, moveOnBoardApi, removeFromBoardApi } from '../api/specialists/specialistsApi'
import {
  patchAllSpecialistBoardCaches,
  QK_BOARD_ROOT,
  restoreSpecialistBoardCaches,
  snapshotSpecialistBoardCaches,
  withoutBoardAttachment,
} from '../domain/specialists/specialistBoardCache'
import type { ManagerSpecialistEntry, SpecialistManagerRef } from '../types/specialist'
import { userFacingMessageFromUnknown } from '../utils/apiUserMessage'
import {
  SPECIALISTS_STUDENTS_ROOT_QUERY_KEY,
  specialistManagersQueryKey,
  specialistStudentsModalQueryKey,
} from '../pages/specialists/specialistQueryKeys'
import { useNotifyToast } from './useNotifyToast'
import { useDelayedActionContext } from './useDelayedActionContext'

type BoardParams = { manager_sub?: string }

type SpecialistProfileHint = {
  display_name?: string | null
  email?: string | null
  avatar_url?: string | null
}

function entryToManagerRef(entry: ManagerSpecialistEntry): SpecialistManagerRef {
  return {
    manager_sub: entry.manager_sub,
    manager_display_name: entry.manager_display_name,
    column_key: entry.column_key,
    status_id: entry.status_id,
    status_title: entry.status_title,
    status_color: entry.status_color,
    created_at: entry.created_at,
  }
}

export function buildPlaceholderEntry(args: {
  specialistSub: string
  managerSub: string
  columnKey: string
  specialist?: SpecialistProfileHint
}): ManagerSpecialistEntry {
  return {
    id: `pending-${crypto.randomUUID()}`,
    specialist_sub: args.specialistSub,
    display_name: args.specialist?.display_name ?? null,
    email: args.specialist?.email ?? null,
    avatar_url: args.specialist?.avatar_url ?? null,
    column_key: args.columnKey,
    position: 0,
    version: 1,
    manager_sub: args.managerSub,
    manager_display_name: null,
    status_id: null,
    status_title: null,
    status_color: null,
    created_at: new Date().toISOString(),
  }
}

export function useSpecialistBoardUndo(options: {
  userSub: string | undefined
  isAdmin: boolean
  specialistSub?: string
}) {
  const { userSub, isAdmin, specialistSub } = options
  const queryClient = useQueryClient()
  const notifyToast = useNotifyToast()
  const managersQk = useMemo(
    () => (specialistSub ? specialistManagersQueryKey(specialistSub) : null),
    [specialistSub],
  )
  const { schedule: scheduleDelayed } = useDelayedActionContext()

  const boardParams = useCallback(
    (managerSub: string | undefined): BoardParams | undefined =>
      isAdmin && managerSub ? { manager_sub: managerSub } : undefined,
    [isAdmin],
  )

  const invalidateBoard = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: QK_BOARD_ROOT })
    void queryClient.refetchQueries({ queryKey: QK_BOARD_ROOT, type: 'active' })
    void queryClient.invalidateQueries({ queryKey: SPECIALISTS_STUDENTS_ROOT_QUERY_KEY })
    void queryClient.invalidateQueries({ queryKey: specialistStudentsModalQueryKey() })
    if (managersQk) {
      void queryClient.invalidateQueries({ queryKey: managersQk })
    }
  }, [managersQk, queryClient])

  const removeManagerFromCaches = useCallback(
    (args: { specialistSub: string; managerSub: string }) => {
      patchAllSpecialistBoardCaches(queryClient, userSub, (prev) =>
        withoutBoardAttachment(prev, args.specialistSub, args.managerSub),
      )
      if (managersQk) {
        queryClient.setQueryData<SpecialistManagerRef[]>(managersQk, (prev) =>
          prev ? prev.filter((m) => m.manager_sub !== args.managerSub) : prev,
        )
      }
    },
    [managersQk, queryClient, userSub],
  )

  const addManagerToCaches = useCallback(
    (created: ManagerSpecialistEntry, args: { specialistSub: string; managerSub: string }) => {
      patchAllSpecialistBoardCaches(queryClient, userSub, (prev) => {
        const rest = withoutBoardAttachment(prev, args.specialistSub, args.managerSub)
        if (rest.some((e) => e.id === created.id)) return rest
        return [...rest, created]
      })
      if (managersQk) {
        queryClient.setQueryData<SpecialistManagerRef[]>(managersQk, (prev) => {
          const list = prev ? prev.filter((m) => m.manager_sub !== args.managerSub) : []
          return [...list, entryToManagerRef(created)]
        })
      }
    },
    [managersQk, queryClient, userSub],
  )

  const snapshotBoardAndManagers = useCallback(() => {
    return {
      board: snapshotSpecialistBoardCaches(queryClient, userSub),
      managers: managersQk
        ? queryClient.getQueryData<SpecialistManagerRef[]>(managersQk)
        : undefined,
    }
  }, [managersQk, queryClient, userSub])

  const restoreBoardAndManagers = useCallback(
    (snap: {
      board: Map<string, ManagerSpecialistEntry[] | undefined>
      managers: SpecialistManagerRef[] | undefined
    }) => {
      restoreSpecialistBoardCaches(queryClient, snap.board)
      if (managersQk && snap.managers !== undefined) {
        queryClient.setQueryData(managersQk, snap.managers)
      }
    },
    [managersQk, queryClient],
  )

  const removeMutation = useMutation({
    mutationFn: ({
      specialistSub,
      managerSub,
    }: {
      specialistSub: string
      managerSub: string
    }) => removeFromBoardApi(specialistSub, boardParams(managerSub)),
    onSuccess: (_data, vars) => {
      removeManagerFromCaches(vars)
      invalidateBoard()
    },
    onError: (e: unknown) => notifyToast(userFacingMessageFromUnknown(e)),
  })

  const scheduleRemoveFromBoard = useCallback(
    (args: {
      specialistSub: string
      managerSub: string
      message?: string
      onUndoClick?: () => void
    }) => {
      const snap = snapshotBoardAndManagers()
      removeManagerFromCaches(args)
      scheduleDelayed({
        message: args.message ?? 'Специалист убран с доски',
        onCommit: () => removeMutation.mutate(args),
        onRevert: () => restoreBoardAndManagers(snap),
        onUndoClick: args.onUndoClick,
      })
    },
    [
      removeManagerFromCaches,
      removeMutation,
      restoreBoardAndManagers,
      scheduleDelayed,
      snapshotBoardAndManagers,
    ],
  )

  const scheduleAddToBoard = useCallback(
    (args: {
      specialistSub: string
      columnKey: string
      managerSub?: string
      specialist?: SpecialistProfileHint
      message?: string
      onUndoClick?: () => void
    }) => {
      const managerSub = args.managerSub ?? userSub
      if (!managerSub) return
      const target = { specialistSub: args.specialistSub, managerSub }
      addManagerToCaches(
        buildPlaceholderEntry({ ...target, columnKey: args.columnKey, specialist: args.specialist }),
        target,
      )
      scheduleDelayed({
        message: args.message ?? 'Специалист добавлен на доску',
        onCommit: async () => {
          try {
            const created = await addToBoardApi(
              { specialist_sub: args.specialistSub, column_key: args.columnKey },
              boardParams(managerSub),
            )
            addManagerToCaches(created, target)
            invalidateBoard()
          } catch (e: unknown) {
            if (!isApiConflictError(e)) {
              removeManagerFromCaches(target)
              notifyToast(userFacingMessageFromUnknown(e))
              return
            }
            try {
              const rows = await listBoardEntries(boardParams(managerSub))
              const entry = rows.find(
                (row) => row.specialist_sub === args.specialistSub && row.manager_sub === managerSub,
              )
              if (!entry) {
                removeManagerFromCaches(target)
                notifyToast(userFacingMessageFromUnknown(e))
                return
              }
              const moved = await moveOnBoardApi(
                args.specialistSub,
                { column_key: args.columnKey, expected_version: entry.version },
                boardParams(managerSub),
              )
              addManagerToCaches(moved, target)
              invalidateBoard()
            } catch (moveError: unknown) {
              removeManagerFromCaches(target)
              notifyToast(userFacingMessageFromUnknown(moveError))
            }
          }
        },
        onRevert: () => removeManagerFromCaches(target),
        onUndoClick: args.onUndoClick,
      })
    },
    [addManagerToCaches, boardParams, invalidateBoard, notifyToast, removeManagerFromCaches, scheduleDelayed, userSub],
  )

  const scheduleAddManagersToBoard = useCallback(
    (args: {
      specialistSub: string
      columnKey: string
      managerSubs: string[]
      existingManagerSubs: ReadonlySet<string>
      message?: string
    }) => {
      const toAdd = args.managerSubs.filter((sub) => !args.existingManagerSubs.has(sub))
      if (toAdd.length === 0) return
      for (const managerSub of toAdd) {
        addManagerToCaches(
          buildPlaceholderEntry({ specialistSub: args.specialistSub, managerSub, columnKey: args.columnKey }),
          { specialistSub: args.specialistSub, managerSub },
        )
      }
      scheduleDelayed({
        message:
          args.message ?? (toAdd.length === 1 ? 'Менеджер добавлен на доску' : 'Менеджеры добавлены на доску'),
        onCommit: async () => {
          for (const managerSub of toAdd) {
            const target = { specialistSub: args.specialistSub, managerSub }
            try {
              const created = await addToBoardApi(
                { specialist_sub: args.specialistSub, column_key: args.columnKey },
                boardParams(managerSub),
              )
              addManagerToCaches(created, target)
            } catch (e: unknown) {
              removeManagerFromCaches(target)
              notifyToast(userFacingMessageFromUnknown(e))
            }
          }
          invalidateBoard()
        },
        onRevert: () => {
          for (const managerSub of toAdd) {
            removeManagerFromCaches({ specialistSub: args.specialistSub, managerSub })
          }
        },
      })
    },
    [addManagerToCaches, boardParams, invalidateBoard, notifyToast, removeManagerFromCaches, scheduleDelayed],
  )

  return {
    invalidateBoard,
    removeMutation,
    scheduleRemoveFromBoard,
    scheduleAddToBoard,
    scheduleAddManagersToBoard,
    snapshotBoardAndManagers,
    restoreBoardAndManagers,
    removeManagerFromCaches,
    boardParams,
  }
}
