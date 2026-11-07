import { useRef, useState, type RefObject } from 'react'
import {
  closestCenter,
  PointerSensor,
  pointerWithin,
  useSensor,
  useSensors,
  type CollisionDetection,
  type DragEndEvent,
  type DragOverEvent,
  type DragStartEvent,
} from '@dnd-kit/core'

import { resolveKanbanBoardCollisions } from '../../domain/kanban/kanbanCollision'
import {
  KANBAN_OTHER_BUCKET,
  kanbanInsertAnchorEquals,
  resolveKanbanInsertAnchorFromPointer,
  visibleKanbanInsertAnchor,
  type KanbanInsertAnchor,
} from '../../domain/kanban/kanbanDisplayCommon'
import {
  capturePortalMainScrollTop,
  clearPortalMainScrollLock,
  useFreezePortalMainScroll,
} from '../../hooks/useFreezePortalMainScroll'
import type { ManagerSpecialistEntry } from '../../types/specialist'
import { kanbanColumnOverlayWidth } from '../tasks/kanban/kanbanDndAnimation'

type Options = {
  columnOrder: string[]
  displayColumnKeys: string[]
  entries: ManagerSpecialistEntry[]
  entriesForColumn: (columnKey: string) => ManagerSpecialistEntry[]
  boardScrollRef: RefObject<HTMLDivElement | null>
  onReorderEntry?: (entryId: string, columnKey: string, anchor: KanbanInsertAnchor) => void
  onReorderColumns?: (columnKeys: string[]) => void
}

export function useSpecialistKanbanDnd({
  columnOrder,
  displayColumnKeys,
  entries,
  entriesForColumn,
  boardScrollRef,
  onReorderEntry,
  onReorderColumns,
}: Options) {
  const [draggingColumnKey, setDraggingColumnKey] = useState<string | null>(null)
  const [overColumnKey, setOverColumnKey] = useState<string | null>(null)
  const [activeEntry, setActiveEntry] = useState<ManagerSpecialistEntry | null>(null)
  const [columnOverlayWidth, setColumnOverlayWidth] = useState<number | null>(null)
  const portalScrollLockRef = useRef<number | null>(null)

  useFreezePortalMainScroll(Boolean(activeEntry || draggingColumnKey), portalScrollLockRef)

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 8 },
    }),
  )

  function handleDragStart(event: DragStartEvent) {
    capturePortalMainScrollTop(portalScrollLockRef)
    if (event.active.data.current?.type === 'column') {
      setDraggingColumnKey(event.active.data.current.status as string)
      setColumnOverlayWidth(kanbanColumnOverlayWidth(event.active.rect.current.initial))
    } else if (event.active.data.current?.type === 'specialist-entry') {
      setActiveEntry((event.active.data.current.entry as ManagerSpecialistEntry) ?? null)
    }
  }

  function handleDragOver(event: DragOverEvent) {
    if (!draggingColumnKey) return
    const overId = event.over ? String(event.over.id) : null
    setOverColumnKey(overId && columnOrder.includes(overId) ? overId : null)
  }

  function handleDragEnd(event: DragEndEvent) {
    setDraggingColumnKey(null)
    setOverColumnKey(null)
    setActiveEntry(null)
    setColumnOverlayWidth(null)
    clearPortalMainScrollLock(portalScrollLockRef)

    const { active, over } = event
    if (!over) return

    if (active.data.current?.type === 'specialist-entry' && onReorderEntry) {
      const entry = active.data.current.entry as ManagerSpecialistEntry
      const overId = String(over.id)
      const overEntry = entries.find((candidate) => candidate.id === overId)
      const targetColumnKey = displayColumnKeys.includes(overId)
        ? overId
        : overEntry?.column_key
      if (!targetColumnKey || targetColumnKey === KANBAN_OTHER_BUCKET) return

      const columnEntries = entriesForColumn(targetColumnKey)
      const translated = active.rect.current.translated
      const activeMidY = translated ? translated.top + translated.height / 2 : null
      const cardRects = new Map<string, { top: number; height: number }>()
      for (const candidate of columnEntries) {
        if (candidate.id === entry.id) continue
        const el = boardScrollRef.current?.querySelector<HTMLElement>(
          `[data-specialist-entry-id="${candidate.id}"]`,
        )
        if (!el) continue
        const rect = el.getBoundingClientRect()
        cardRects.set(candidate.id, { top: rect.top, height: rect.height })
      }
      if (cardRects.size === 0 && overEntry) {
        cardRects.set(overEntry.id, over.rect)
      }

      const anchor = displayColumnKeys.includes(overId)
        ? cardRects.size > 0
          ? resolveKanbanInsertAnchorFromPointer(
              columnEntries,
              entry.id,
              activeMidY,
              cardRects,
            )
          : { afterTaskId: null, beforeTaskId: null }
        : resolveKanbanInsertAnchorFromPointer(columnEntries, entry.id, activeMidY, cardRects)

      if (targetColumnKey === entry.column_key) {
        const currentAnchor = visibleKanbanInsertAnchor(
          entriesForColumn(entry.column_key),
          entry.id,
        )
        if (kanbanInsertAnchorEquals(anchor, currentAnchor)) return
      }
      onReorderEntry(entry.id, targetColumnKey, anchor)
      return
    }

    if (active.data.current?.type !== 'column') return

    const draggedKey = active.data.current.status as string
    const overKey = String(over.id)
    if (draggedKey === overKey || !columnOrder.includes(overKey)) return

    const fromIdx = columnOrder.indexOf(draggedKey)
    const toIdx = columnOrder.indexOf(overKey)
    if (fromIdx < 0 || toIdx < 0) return

    const newOrder = [...columnOrder]
    newOrder.splice(fromIdx, 1)
    newOrder.splice(toIdx, 0, draggedKey)
    onReorderColumns?.(newOrder)
  }

  function handleDragCancel() {
    setDraggingColumnKey(null)
    setOverColumnKey(null)
    setActiveEntry(null)
    setColumnOverlayWidth(null)
    clearPortalMainScrollLock(portalScrollLockRef)
  }

  function getDropSide(colKey: string): 'left' | 'right' | null {
    if (!draggingColumnKey || overColumnKey !== colKey || draggingColumnKey === colKey) {
      return null
    }
    const from = columnOrder.indexOf(draggingColumnKey)
    const to = columnOrder.indexOf(colKey)
    return from < to ? 'right' : 'left'
  }

  const collisionDetection: CollisionDetection = (args) => {
    const activeType =
      typeof args.active.data.current?.type === 'string' ? args.active.data.current.type : undefined
    const columnIds = new Set(activeType === 'column' ? columnOrder : displayColumnKeys)
    return resolveKanbanBoardCollisions({
      activeType,
      activeId: String(args.active.id),
      pointerHits: pointerWithin(args),
      closestHits: closestCenter(args),
      columnIds,
      taskIdsInColumn: (columnKey) => new Set(entriesForColumn(columnKey).map((entry) => entry.id)),
    })
  }

  return {
    sensors,
    activeEntry,
    collisionDetection,
    handleDragStart,
    handleDragOver,
    handleDragEnd,
    handleDragCancel,
    draggingColumnKey,
    columnOverlayWidth,
    getDropSide,
  }
}
