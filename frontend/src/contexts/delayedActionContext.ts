import { createContext } from 'react'

import type { DelayedActionPayload } from '../hooks/useDelayedAction'

export type DelayedActionContextValue = {
  pendingList: { id: string; message: string; canUndo: boolean; actionLabel?: string }[]
  schedule: (payload: DelayedActionPayload) => void
  undo: (id: string) => void
  runAction: (id: string) => void
  optimisticallyHiddenIds: ReadonlySet<string>
  hideOptimistically: (id: string) => void
  showOptimistically: (id: string) => void
}

export const DelayedActionContext = createContext<DelayedActionContextValue | null>(null)
