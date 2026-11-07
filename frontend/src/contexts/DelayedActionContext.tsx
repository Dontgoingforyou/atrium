import {
  useCallback,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

import { ActionUndoSnackbarStack } from '../components/common/ActionUndoSnackbar'
import { useDelayedAction } from '../hooks/useDelayedAction'
import { DelayedActionContext } from './delayedActionContext'

export function DelayedActionProvider({ children }: { children: ReactNode }) {
  const { pendingList, schedule, undo, runAction } = useDelayedAction()
  const [optimisticallyHiddenIds, setOptimisticallyHiddenIds] = useState<ReadonlySet<string>>(
    () => new Set(),
  )

  const hideOptimistically = useCallback((id: string) => {
    setOptimisticallyHiddenIds((prev) => {
      if (prev.has(id)) return prev
      const next = new Set(prev)
      next.add(id)
      return next
    })
  }, [])

  const showOptimistically = useCallback((id: string) => {
    setOptimisticallyHiddenIds((prev) => {
      if (!prev.has(id)) return prev
      const next = new Set(prev)
      next.delete(id)
      return next
    })
  }, [])

  const pendingListPublic = useMemo(
    () =>
      pendingList.map((p) => ({
        id: p.id,
        message: p.message,
        canUndo: p.onRevert != null,
        actionLabel: p.actionLabel,
      })),
    [pendingList],
  )

  const value = useMemo(
    () => ({
      pendingList: pendingListPublic,
      schedule,
      undo,
      runAction,
      optimisticallyHiddenIds,
      hideOptimistically,
      showOptimistically,
    }),
    [
      pendingListPublic,
      schedule,
      undo,
      runAction,
      optimisticallyHiddenIds,
      hideOptimistically,
      showOptimistically,
    ],
  )

  return (
    <DelayedActionContext.Provider value={value}>
      {children}
      <ActionUndoSnackbarStack
        items={pendingListPublic}
        onUndo={undo}
        onAction={runAction}
      />
    </DelayedActionContext.Provider>
  )
}
