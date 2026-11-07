import { useCallback, useEffect, useState } from 'react'
import type { DropAnimation } from '@dnd-kit/core'
import { defaultAnimateLayoutChanges, type AnimateLayoutChanges } from '@dnd-kit/sortable'

/** Overlay долетает в слот. Карточки оставляют dropAnimation=null из‑за scrollIntoView. */
export const KANBAN_COLUMN_DROP_DURATION_MS = 220

export const KANBAN_COLUMN_DROP_SETTLE_BUFFER_MS = 40

/** Разворот из компактного превью в полную высоту колонки. */
export const KANBAN_COLUMN_UNFOLD_DURATION_MS = 320

export const KANBAN_COLUMN_OVERLAY_FALLBACK_WIDTH_PX = 280

export const KANBAN_COLUMN_DROP_ANIMATION: DropAnimation = {
  duration: KANBAN_COLUMN_DROP_DURATION_MS,
  easing: 'cubic-bezier(0.25, 1, 0.5, 1)',
  sideEffects: () => () => {},
}

export function kanbanColumnOverlayWidth(
  rect: { width: number } | null | undefined,
): number {
  return rect?.width ?? KANBAN_COLUMN_OVERLAY_FALLBACK_WIDTH_PX
}

/** После persist порядка колонка и соседи доезжают transform'ом, а не прыгают. */
export const kanbanColumnAnimateLayoutChanges: AnimateLayoutChanges = (args) =>
  defaultAnimateLayoutChanges({ ...args, wasDragging: true })

/** Скрыта, пока overlay долетает; в фазе unfold снова видна (clip-path). */
export function isKanbanColumnDropHidden(
  status: string,
  settlingColumnId: string | null,
  unfoldingColumnId: string | null,
): boolean {
  return settlingColumnId === status && unfoldingColumnId !== status
}

export function useKanbanColumnDropAnimation(): {
  dropAnimation: DropAnimation | null
  settlingColumnId: string | null
  unfoldingColumnId: string | null
  markColumnDragStart: () => void
  markNonColumnDragStart: () => void
  finishColumnDrop: (columnId: string) => void
  cancelColumnDrop: () => void
} {
  const [dropAnimation, setDropAnimation] = useState<DropAnimation | null>(null)
  const [settlingColumnId, setSettlingColumnId] = useState<string | null>(null)
  const [unfoldingColumnId, setUnfoldingColumnId] = useState<string | null>(null)

  const cancelColumnDrop = useCallback(() => {
    setDropAnimation(null)
    setSettlingColumnId(null)
    setUnfoldingColumnId(null)
  }, [])

  const markColumnDragStart = useCallback(() => {
    cancelColumnDrop()
    setDropAnimation(KANBAN_COLUMN_DROP_ANIMATION)
  }, [cancelColumnDrop])

  const markNonColumnDragStart = useCallback(() => {
    cancelColumnDrop()
  }, [cancelColumnDrop])

  const finishColumnDrop = useCallback((columnId: string) => {
    setSettlingColumnId(columnId)
  }, [])

  useEffect(() => {
    if (!settlingColumnId || unfoldingColumnId) return
    const timer = window.setTimeout(() => {
      setDropAnimation(null)
      setUnfoldingColumnId(settlingColumnId)
    }, KANBAN_COLUMN_DROP_DURATION_MS + KANBAN_COLUMN_DROP_SETTLE_BUFFER_MS)
    return () => window.clearTimeout(timer)
  }, [settlingColumnId, unfoldingColumnId])

  useEffect(() => {
    if (!unfoldingColumnId) return
    const timer = window.setTimeout(() => {
      setSettlingColumnId(null)
      setUnfoldingColumnId(null)
      setDropAnimation(null)
    }, KANBAN_COLUMN_UNFOLD_DURATION_MS)
    return () => window.clearTimeout(timer)
  }, [unfoldingColumnId])

  return {
    dropAnimation,
    settlingColumnId,
    unfoldingColumnId,
    markColumnDragStart,
    markNonColumnDragStart,
    finishColumnDrop,
    cancelColumnDrop,
  }
}
