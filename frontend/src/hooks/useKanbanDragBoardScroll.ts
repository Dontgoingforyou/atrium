import { useCallback, useEffect, useRef, type RefObject } from 'react'

import {
  nextKanbanBoardScrollLeft,
  resolveKanbanDragEdgeDirection,
  type KanbanDragEdgeDirection,
} from '../domain/kanban/kanbanDragScroll'
import {
  dampWheelDelta,
  resolveDragBoardWheelDelta,
} from './useInertialWheelScroll'

export function useKanbanDragBoardScroll(
  boardScrollRef: RefObject<HTMLElement | null>,
  active: boolean,
): {
  updateEdgeFromActiveCenterX: (centerX: number | null) => void
  stopEdgeScroll: () => void
} {
  const edgeDirRef = useRef<KanbanDragEdgeDirection>(null)
  const rafRef = useRef<number | null>(null)
  const tickEdgeRef = useRef<() => void>(() => {})

  const stopEdgeLoop = useCallback(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current)
      rafRef.current = null
    }
  }, [])

  const stopEdgeScroll = useCallback(() => {
    edgeDirRef.current = null
    stopEdgeLoop()
  }, [stopEdgeLoop])

  const tickEdge = useCallback(() => {
    const el = boardScrollRef.current
    const dir = edgeDirRef.current
    if (!el || !dir) {
      rafRef.current = null
      return
    }
    el.scrollLeft = nextKanbanBoardScrollLeft(
      el.scrollLeft,
      el.scrollWidth,
      el.clientWidth,
      dir,
    )
    rafRef.current = requestAnimationFrame(() => {
      tickEdgeRef.current()
    })
  }, [boardScrollRef])

  useEffect(() => {
    tickEdgeRef.current = tickEdge
  }, [tickEdge])

  const ensureEdgeLoop = useCallback(() => {
    if (rafRef.current !== null) return
    if (!edgeDirRef.current) return
    rafRef.current = requestAnimationFrame(() => {
      tickEdgeRef.current()
    })
  }, [])

  const updateEdgeFromActiveCenterX = useCallback(
    (centerX: number | null) => {
      const el = boardScrollRef.current
      if (!el || centerX === null) {
        stopEdgeScroll()
        return
      }
      const rect = el.getBoundingClientRect()
      const next = resolveKanbanDragEdgeDirection(
        { left: rect.left, right: rect.right },
        centerX,
      )
      edgeDirRef.current = next
      if (!next) {
        stopEdgeLoop()
        return
      }
      ensureEdgeLoop()
    },
    [boardScrollRef, ensureEdgeLoop, stopEdgeLoop, stopEdgeScroll],
  )

  useEffect(() => {
    if (!active) {
      stopEdgeScroll()
      return
    }

    const onWheel = (e: WheelEvent) => {
      const el = boardScrollRef.current
      if (!el) return
      const rawDelta = resolveDragBoardWheelDelta(e.deltaX, e.deltaY, e.shiftKey)
      if (rawDelta === null) return
      e.preventDefault()
      el.scrollLeft += dampWheelDelta(rawDelta)
    }

    document.addEventListener('wheel', onWheel, { capture: true, passive: false })
    return () => {
      document.removeEventListener('wheel', onWheel, { capture: true })
      stopEdgeScroll()
    }
  }, [active, boardScrollRef, stopEdgeScroll])

  return { updateEdgeFromActiveCenterX, stopEdgeScroll }
}
