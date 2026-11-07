/** Зона у края доски, где включается непрерывный горизонтальный auto-scroll при DnD. */
export const KANBAN_DRAG_EDGE_MARGIN_PX = 64

/** Шаг scrollLeft за один кадр rAF при edge-скролле. */
export const KANBAN_DRAG_EDGE_STEP_PX = 14

export type KanbanDragEdgeDirection = 'left' | 'right' | null

/**
 * Направление edge-скролла по центру translated-rect карточки относительно bounds доски.
 * null — указатель/карточка не у края.
 */
export function resolveKanbanDragEdgeDirection(
  boardRect: { left: number; right: number },
  activeCenterX: number,
  marginPx: number = KANBAN_DRAG_EDGE_MARGIN_PX,
): KanbanDragEdgeDirection {
  if (activeCenterX < boardRect.left + marginPx) return 'left'
  if (activeCenterX > boardRect.right - marginPx) return 'right'
  return null
}

export function dragPointerX(
  activatorClientX: number | null | undefined,
  deltaX: number,
  translated: { left: number; width: number } | null | undefined,
): number | null {
  if (activatorClientX != null && Number.isFinite(activatorClientX)) {
    return activatorClientX + deltaX
  }
  if (!translated) return null
  return translated.left + translated.width / 2
}

export function clientXFromActivatorEvent(event: Event): number | null {
  if ('clientX' in event && typeof event.clientX === 'number') return event.clientX
  const touchLike = event as { touches?: Array<{ clientX: number }>; changedTouches?: Array<{ clientX: number }> }
  const t = touchLike.touches?.[0] ?? touchLike.changedTouches?.[0]
  return t && typeof t.clientX === 'number' ? t.clientX : null
}

/** Следующий scrollLeft с учётом границ контейнера. */
export function nextKanbanBoardScrollLeft(
  scrollLeft: number,
  scrollWidth: number,
  clientWidth: number,
  direction: Exclude<KanbanDragEdgeDirection, null>,
  stepPx: number = KANBAN_DRAG_EDGE_STEP_PX,
): number {
  const max = Math.max(0, scrollWidth - clientWidth)
  if (direction === 'left') return Math.max(0, scrollLeft - stepPx)
  return Math.min(max, scrollLeft + stepPx)
}
