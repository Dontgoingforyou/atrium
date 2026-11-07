import { useCallback, useRef, useState, type RefObject } from 'react'
import {
  closestCenter,
  PointerSensor,
  pointerWithin,
  useSensor,
  useSensors,
  type CollisionDetection,
  type DragEndEvent,
  type DragMoveEvent,
  type DragOverEvent,
  type DragStartEvent,
} from '@dnd-kit/core'

import type { PortalTask, PortalTaskColumn } from '../../../types/task'
import { getTaskColumnColor, getTaskColumnTitle } from '../../../domain/tasks/taskColumns'
import { resolveKanbanBoardCollisions } from '../../../domain/kanban/kanbanCollision'
import { clientXFromActivatorEvent, dragPointerX } from '../../../domain/kanban/kanbanDragScroll'
import {
  KANBAN_OTHER_BUCKET,
  resolveKanbanInsertAnchorFromPointer,
  kanbanInsertAnchorEquals,
  visibleKanbanInsertAnchor,
  kanbanReorderPeerTasks,
  type KanbanInsertAnchor,
} from '../../../domain/kanban/kanbanDisplayCommon'
import {
  useFreezePortalMainScroll,
  capturePortalMainScrollTop,
  clearPortalMainScrollLock,
} from '../../../hooks/useFreezePortalMainScroll'
import { useKanbanDragBoardScroll } from '../../../hooks/useKanbanDragBoardScroll'
import {
  kanbanColumnOverlayWidth,
  useKanbanColumnDropAnimation,
} from './kanbanDndAnimation'

type ColumnOverlayState = {
  title: string
  color: string
  itemCount: number
  width: number
}

type Options = {
  statusOrder: string[]
  columns: PortalTaskColumn[]
  tasks: PortalTask[]
  tasksInColumn: (status: string) => PortalTask[]
  taskById: Map<string, PortalTask>
  subtasksByParentId: Map<string, PortalTask[]>
  subtasksFlat: boolean
  titleOverrides: Record<string, string>
  taskIdsInColumnWithNested: (status: string) => Set<string>
  boardScrollRef: RefObject<HTMLDivElement | null>
  onReorder: (taskId: string, newStatus: string, anchor: KanbanInsertAnchor) => void
  onReorderColumns?: (newStatusOrder: string[]) => void
}

export function useTaskKanbanDnd({
  statusOrder,
  columns,
  tasks,
  tasksInColumn,
  taskById,
  subtasksByParentId,
  subtasksFlat,
  titleOverrides,
  taskIdsInColumnWithNested,
  boardScrollRef,
  onReorder,
  onReorderColumns,
}: Options) {
  const [draggingColumnStatus, setDraggingColumnStatus] = useState<string | null>(null)
  const [overColumnStatus, setOverColumnStatus] = useState<string | null>(null)
  const [activeTask, setActiveTask] = useState<PortalTask | null>(null)
  const [columnOverlay, setColumnOverlay] = useState<ColumnOverlayState | null>(null)
  const {
    dropAnimation: columnDropAnimation,
    settlingColumnId,
    unfoldingColumnId,
    markColumnDragStart,
    markNonColumnDragStart,
    finishColumnDrop,
    cancelColumnDrop,
  } = useKanbanColumnDropAnimation()
  const portalScrollLockRef = useRef<number | null>(null)
  const suppressNavAfterDragRef = useRef<string | null>(null)

  const dragScrollActive = Boolean(activeTask || draggingColumnStatus)
  useFreezePortalMainScroll(dragScrollActive, portalScrollLockRef)
  const { updateEdgeFromActiveCenterX, stopEdgeScroll } = useKanbanDragBoardScroll(
    boardScrollRef,
    dragScrollActive,
  )

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 4 },
    }),
  )

  const kanbanDndAutoScroll = {
    enabled: true,
    layoutShiftCompensation: false as const,
    canScroll: (el: Element) => el === boardScrollRef.current,
  }

  const collectCardRects = useCallback(
    (peers: PortalTask[], excludeTaskId: string): Map<string, { top: number; height: number }> => {
      const cardRects = new Map<string, { top: number; height: number }>()
      const scrollRoot = boardScrollRef.current
      if (!scrollRoot) return cardRects
      for (const t of peers) {
        if (t.id === excludeTaskId) continue
        const el = scrollRoot.querySelector<HTMLElement>(`[data-task-id="${t.id}"]`)
        if (!el) continue
        const rect = el.getBoundingClientRect()
        cardRects.set(t.id, { top: rect.top, height: rect.height })
      }
      return cardRects
    },
    [boardScrollRef],
  )

  function peersForReorder(dragged: PortalTask, columnStatus: string): PortalTask[] {
    return kanbanReorderPeerTasks(
      dragged,
      columnStatus,
      tasksInColumn(columnStatus),
      subtasksByParentId,
      taskById,
      subtasksFlat,
    )
  }

  function updateDragEdgeScroll(event: DragMoveEvent | DragOverEvent) {
    const type = event.active.data.current?.type
    if (type !== 'column' && type !== 'task') return
    updateEdgeFromActiveCenterX(
      dragPointerX(
        clientXFromActivatorEvent(event.activatorEvent),
        event.delta.x,
        event.active.rect.current.translated,
      ),
    )
  }

  function resetDragUi() {
    setDraggingColumnStatus(null)
    setOverColumnStatus(null)
    setActiveTask(null)
    setColumnOverlay(null)
    stopEdgeScroll()
    clearPortalMainScrollLock(portalScrollLockRef)
  }

  function handleDragStart(event: DragStartEvent) {
    capturePortalMainScrollTop(portalScrollLockRef)
    if (event.active.data.current?.type === 'column') {
      markColumnDragStart()
      const status = event.active.data.current.status as string
      setDraggingColumnStatus(status)
      setColumnOverlay({
        title: getTaskColumnTitle(status, columns, titleOverrides),
        color: getTaskColumnColor(status, columns),
        itemCount: tasksInColumn(status).length,
        width: kanbanColumnOverlayWidth(event.active.rect.current.initial),
      })
    } else if (event.active.data.current?.type === 'task') {
      markNonColumnDragStart()
      setActiveTask((event.active.data.current.task as PortalTask) ?? null)
    }
  }

  function handleDragMove(event: DragMoveEvent) {
    updateDragEdgeScroll(event)
  }

  function handleDragOver(event: DragOverEvent) {
    if (event.active.data.current?.type === 'column') {
      const overId = event.over ? String(event.over.id) : null
      if (overId === KANBAN_OTHER_BUCKET) {
        setOverColumnStatus(null)
      } else {
        setOverColumnStatus(overId && statusOrder.includes(overId) ? overId : null)
      }
    }
    updateDragEdgeScroll(event)
  }

  function applyColumnReorder(draggedStatus: string, overStatus: string) {
    if (overStatus === KANBAN_OTHER_BUCKET) return
    if (draggedStatus === overStatus || !statusOrder.includes(overStatus)) return
    const orderSansOther = statusOrder.filter((s) => s !== KANBAN_OTHER_BUCKET)
    const fromIdx = orderSansOther.indexOf(draggedStatus)
    const toIdx = orderSansOther.indexOf(overStatus)
    if (fromIdx < 0 || toIdx < 0) return
    const newOrder = [...orderSansOther]
    newOrder.splice(fromIdx, 1)
    newOrder.splice(toIdx, 0, draggedStatus)
    onReorderColumns?.(newOrder)
    if (toIdx === 0) {
      requestAnimationFrame(() => {
        boardScrollRef.current?.scrollTo({ left: 0, behavior: 'smooth' })
      })
    }
  }

  function applyTaskReorder(event: DragEndEvent, over: NonNullable<DragEndEvent['over']>) {
    const overId = String(over.id)
    const taskId = String(event.active.id)
    const task = tasks.find((t) => t.id === taskId)
    if (!task || overId === KANBAN_OTHER_BUCKET) return

    let newStatus: string
    let anchor: KanbanInsertAnchor

    if (statusOrder.includes(overId)) {
      newStatus = overId
      if (newStatus !== task.status) {
        anchor = { afterTaskId: null, beforeTaskId: null }
      } else {
        const peers = peersForReorder(task, newStatus)
        const translated = event.active.rect.current.translated
        const activeMidY = translated ? translated.top + translated.height / 2 : null
        const cardRects = collectCardRects(peers, taskId)
        anchor =
          cardRects.size > 0
            ? resolveKanbanInsertAnchorFromPointer(peers, taskId, activeMidY, cardRects)
            : { afterTaskId: null, beforeTaskId: null }
      }
    } else {
      const overTask = tasks.find((t) => t.id === overId)
      if (!overTask) return
      newStatus = overTask.status
      if (newStatus !== task.status) {
        anchor = { afterTaskId: null, beforeTaskId: null }
      } else {
        const peers = peersForReorder(task, newStatus)
        const translated = event.active.rect.current.translated
        const activeMidY = translated ? translated.top + translated.height / 2 : null
        let cardRects = collectCardRects(peers, taskId)
        if (cardRects.size === 0) {
          cardRects = new Map([[overId, over.rect]])
        }
        anchor = resolveKanbanInsertAnchorFromPointer(peers, taskId, activeMidY, cardRects)
      }
    }

    if (newStatus === task.status) {
      const currentAnchor = visibleKanbanInsertAnchor(peersForReorder(task, task.status), taskId)
      if (kanbanInsertAnchorEquals(anchor, currentAnchor)) return
    }
    onReorder(taskId, newStatus, anchor)
  }

  function handleDragEnd(event: DragEndEvent) {
    const droppedColumnStatus =
      event.active.data.current?.type === 'column' &&
      typeof event.active.data.current?.status === 'string'
        ? event.active.data.current.status
        : undefined
    resetDragUi()
    if (droppedColumnStatus) finishColumnDrop(droppedColumnStatus)
    else cancelColumnDrop()

    if (event.active.data.current?.type === 'task') {
      suppressNavAfterDragRef.current = String(event.active.id)
      window.setTimeout(() => {
        if (suppressNavAfterDragRef.current === String(event.active.id)) {
          suppressNavAfterDragRef.current = null
        }
      }, 400)
    }

    const { active, over } = event
    if (!over) return

    if (active.data.current?.type === 'column') {
      applyColumnReorder(active.data.current.status as string, String(over.id))
      return
    }
    applyTaskReorder(event, over)
  }

  function handleDragCancel() {
    resetDragUi()
    cancelColumnDrop()
  }

  function getDropSide(status: string): 'left' | 'right' | null {
    if (status === KANBAN_OTHER_BUCKET) return null
    if (!draggingColumnStatus || overColumnStatus !== status || draggingColumnStatus === status) {
      return null
    }
    const from = statusOrder.indexOf(draggingColumnStatus)
    const to = statusOrder.indexOf(status)
    return from < to ? 'right' : 'left'
  }

  const collisionDetection: CollisionDetection = (args) =>
    resolveKanbanBoardCollisions({
      activeType:
        typeof args.active.data.current?.type === 'string'
          ? args.active.data.current.type
          : undefined,
      activeId: String(args.active.id),
      pointerHits: pointerWithin(args),
      closestHits: closestCenter(args),
      columnIds: new Set(statusOrder),
      taskIdsInColumn: taskIdsInColumnWithNested,
    })

  return {
    sensors,
    kanbanDndAutoScroll,
    collisionDetection,
    handleDragStart,
    handleDragMove,
    handleDragOver,
    handleDragEnd,
    handleDragCancel,
    getDropSide,
    activeTask,
    columnOverlay,
    columnDropAnimation,
    settlingColumnId,
    unfoldingColumnId,
    suppressNavAfterDragRef,
    dragScrollActive,
  }
}
