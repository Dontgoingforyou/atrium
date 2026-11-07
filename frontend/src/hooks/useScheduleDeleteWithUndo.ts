import { useCallback } from 'react'

import { playUiSound } from '../utils/sound/uiSounds'
import { useDelayedActionContext } from './useDelayedActionContext'

type ScheduleDeleteWithUndoArgs = {
  message: string
  optimistic: () => void
  revert: () => void
  commit: () => void
  onUndoClick?: () => void
}

/** Отложенное удаление с optimistic UI и 5-сек undo. */
export function useScheduleDeleteWithUndo() {
  const { schedule } = useDelayedActionContext()

  return useCallback(
    (args: ScheduleDeleteWithUndoArgs) => {
      playUiSound('error')
      args.optimistic()
      schedule({
        message: args.message,
        onCommit: args.commit,
        onRevert: args.revert,
        onUndoClick: args.onUndoClick,
      })
    },
    [schedule],
  )
}
