import { useCallback } from 'react'

import { playUiSound } from '../utils/sound/uiSounds'
import { useDelayedActionContext } from './useDelayedActionContext'

type NotifyToastOptions = {
  actionLabel?: string
  onAction?: () => void
  tone?: 'success' | 'error'
  /** Без звука: смысловой патч уже сыграл на confirm (ConfirmDialog confirmSound). */
  silent?: boolean
}

export function useNotifyToast() {
  const { schedule } = useDelayedActionContext()

  return useCallback(
    (message: string, options?: NotifyToastOptions) => {
      if (!options?.silent) {
        playUiSound(options?.tone === 'error' ? 'error' : 'success')
      }
      schedule({
        message,
        onCommit: () => {},
        actionLabel: options?.actionLabel,
        onAction: options?.onAction,
      })
    },
    [schedule],
  )
}
