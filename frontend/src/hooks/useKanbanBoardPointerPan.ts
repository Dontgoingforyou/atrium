import { useRef, useState, type PointerEvent as ReactPointerEvent, type RefObject } from 'react'

export function useKanbanBoardPointerPan(
  boardScrollRef: RefObject<HTMLDivElement | null>,
  skipClosest: readonly string[],
): {
  boardPanning: boolean
  onPointerDown: (e: ReactPointerEvent<HTMLDivElement>) => void
  onPointerMove: (e: ReactPointerEvent<HTMLDivElement>) => void
  onPointerUp: (e: ReactPointerEvent<HTMLDivElement>) => void
  onPointerLeave: (e: ReactPointerEvent<HTMLDivElement>) => void
} {
  const panStateRef = useRef({ active: false, startX: 0, startScrollLeft: 0 })
  const [boardPanning, setBoardPanning] = useState(false)

  function onPointerDown(e: ReactPointerEvent<HTMLDivElement>) {
    if (e.button !== 0) return
    const t = e.target as HTMLElement
    if (skipClosest.some((sel) => t.closest(sel))) return

    const el = boardScrollRef.current
    if (!el) return
    el.setPointerCapture(e.pointerId)
    panStateRef.current = {
      active: true,
      startX: e.clientX,
      startScrollLeft: el.scrollLeft,
    }
    setBoardPanning(true)
  }

  function onPointerMove(e: ReactPointerEvent<HTMLDivElement>) {
    if (!panStateRef.current.active) return
    const el = boardScrollRef.current
    if (!el) return
    el.scrollLeft = panStateRef.current.startScrollLeft - (e.clientX - panStateRef.current.startX)
  }

  function onPointerUp(e: ReactPointerEvent<HTMLDivElement>) {
    if (!panStateRef.current.active) return
    panStateRef.current.active = false
    setBoardPanning(false)
    const el = boardScrollRef.current
    if (!el) return
    try {
      el.releasePointerCapture(e.pointerId)
    } catch {
      /* pointer уже отпущен — capture снят браузером */
    }
  }

  function onPointerLeave(e: ReactPointerEvent<HTMLDivElement>) {
    if (panStateRef.current.active && e.buttons === 0) onPointerUp(e)
  }

  return {
    boardPanning,
    onPointerDown,
    onPointerMove,
    onPointerUp,
    onPointerLeave,
  }
}
