import { useContext } from 'react'

import {
  DelayedActionContext,
  type DelayedActionContextValue,
} from '../contexts/delayedActionContext'

export function useDelayedActionContext(): DelayedActionContextValue {
  const ctx = useContext(DelayedActionContext)
  if (!ctx) {
    throw new Error('useDelayedActionContext: обёрните дерево в DelayedActionProvider')
  }
  return ctx
}
