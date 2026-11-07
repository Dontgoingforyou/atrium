import { useCallback, useEffect, useState } from 'react'

import { DelayedActionQueue, DEFAULT_DELAYED_ACTION_MS } from './delayedActionQueue'
import type { DelayedActionPayload, PendingDelayedAction } from './delayedActionQueue'

export { DEFAULT_DELAYED_ACTION_MS }
export type { DelayedActionPayload, PendingDelayedAction }

/**
 * Очередь отложенных действий: у каждого свой таймер и snackbar.
 * Новое действие не отменяет предыдущие — они закрываются по очереди (undo / commit).
 * Этот хук — тонкая обвязка, синхронизирующая её с состоянием компонента.
 */
export function useDelayedAction(delayMs: number = DEFAULT_DELAYED_ACTION_MS) {
  const [pendingList, setPendingList] = useState<PendingDelayedAction[]>([])
  // Lazy useState-инициализатор (не ref) — создаёт очередь один раз, без обращения
  // к ref.current во время рендера.
  const [queue] = useState(() => new DelayedActionQueue(delayMs, setPendingList))

  const schedule = useCallback((payload: DelayedActionPayload) => {
    queue.schedule(payload)
  }, [queue])

  const undo = useCallback((id: string) => {
    queue.undo(id)
  }, [queue])

  const runAction = useCallback((id: string) => {
    queue.runAction(id)
  }, [queue])

  useEffect(() => {
    const onBeforeUnload = () => queue.clearTimersOnly()
    window.addEventListener('beforeunload', onBeforeUnload)
    return () => {
      window.removeEventListener('beforeunload', onBeforeUnload)
      queue.cancelAll()
    }
  }, [queue])

  return {
    pendingList,
    schedule,
    undo,
    runAction,
  }
}
