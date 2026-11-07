import { useCallback, useSyncExternalStore } from 'react'

/**
 * Раскрытые ветки дерева документов — только на время SPA-сессии
 * (client-side навигация сохраняет; F5 / полный remount → всё свёрнуто).
 */
const expandedIds = new Set<string>()
let version = 0
const listeners = new Set<() => void>()

function emit() {
  version += 1
  for (const l of listeners) {
    l()
  }
}

function subscribe(onStoreChange: () => void): () => void {
  listeners.add(onStoreChange)
  return () => {
    listeners.delete(onStoreChange)
  }
}

function getSnapshot(): number {
  return version
}

export function useNavTreeBranchCollapse() {
  useSyncExternalStore(subscribe, getSnapshot, getSnapshot)

  const isCollapsed = useCallback((id: string) => !expandedIds.has(id), [])

  const toggle = useCallback((id: string) => {
    if (expandedIds.has(id)) {
      expandedIds.delete(id)
    } else {
      expandedIds.add(id)
    }
    emit()
  }, [])

  return { isCollapsed, toggle }
}
