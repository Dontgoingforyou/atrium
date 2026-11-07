import { useCallback, useEffect, useMemo, useRef } from 'react'
import { DndContext, DragOverlay } from '@dnd-kit/core'
import { SortableContext, horizontalListSortingStrategy, verticalListSortingStrategy } from '@dnd-kit/sortable'

import type {
  PortalTask,
  PortalTaskColumn,
  TaskBoardPref,
  TaskColumnCreate,
  TaskColumnUpdate,
} from '../../../types/task'
import { partitionParentSubtasks } from '../../../domain/tasks/taskBoardPref'
import { isSubtaskProgressDone } from '../../../domain/tasks/taskColumns'
import { KANBAN_OTHER_BUCKET, type KanbanInsertAnchor } from '../../../domain/kanban/kanbanDisplayCommon'
import { firstNonEmptyColumnStatus } from '../../../domain/kanban/kanbanOverdueFocus'
import { useInertialWheelScroll } from '../../../hooks/useInertialWheelScroll'
import { useKanbanColumnModel } from '../../../hooks/useKanbanColumnModel'
import { useKanbanScrollPersist } from '../../../hooks/useKanbanScrollPersist'
import { useKanbanBoardPointerPan } from '../../../hooks/useKanbanBoardPointerPan'
import type { PortalUserShort } from '../../../api/usersApi'
import { AddColumnCard, KanbanColumn, type KanbanColumnExportFilters } from './KanbanColumn'
import { KanbanCard } from './KanbanCard'
import { KanbanColumnDragOverlay } from './KanbanColumnDragOverlay'
import { KanbanDragOverlay } from './KanbanDragOverlay'
import { isKanbanColumnDropHidden } from './kanbanDndAnimation'
import { useTaskKanbanDnd } from './useTaskKanbanDnd'
import boardStyles from '@/styles/modules/tasks/TasksPageKanbanCards.module.css'
import columnStyles from '@/styles/modules/tasks/TasksPageKanbanColumns.module.css'

export function KanbanBoard({
  tasks,
  columns,
  onReorder,
  onUpdateColumn,
  onDeleteColumn,
  onCreateColumn,
  onReorderColumns,
  onCreateTask,
  onOpenCreateModal,
  onOpenTask,
  onOpenTaskDetail,
  isUpdating,
  canEditColumns = false,
  canEditKpi = false,
  allowPersonalColumnDrag = false,
  boardPref,
  showAllHiddenColumns = false,
  statusOrderOverride,
  getTasksForStatus,
  titleOverrides,
  assigneeDirectory,
  highlightTaskId,
  showColumnAddButton = true,
  kanbanScrollStorageKey,
  onSpecialistDropped,
  canDeleteTask,
  onDeleteTask,
  canEditTask,
  exportFilters,
  scrollToFirstNonEmptyColumn = false,
}: {
  tasks: PortalTask[]
  columns: PortalTaskColumn[]
  onReorder: (taskId: string, newStatus: string, anchor: KanbanInsertAnchor) => void
  onUpdateColumn?: (id: string, data: TaskColumnUpdate) => void
  onDeleteColumn?: (id: string) => void
  onCreateColumn?: (data: TaskColumnCreate) => void
  onReorderColumns?: (newStatusOrder: string[]) => void
  onCreateTask?: (title: string, status: string) => Promise<string>
  onOpenCreateModal?: (status: string) => void
  onOpenTask?: (taskId: string) => void
  onOpenTaskDetail?: (taskId: string) => void
  isUpdating: boolean
  canEditColumns?: boolean
  canEditKpi?: boolean
  allowPersonalColumnDrag?: boolean
  /** Если не переданы ``statusOrderOverride`` и ``getTasksForStatus`` — строится через ``useKanbanColumnModel`` / ``computeKanbanDisplay``. */
  boardPref?: TaskBoardPref | null
  showAllHiddenColumns?: boolean
  statusOrderOverride?: string[]
  getTasksForStatus?: (status: string) => PortalTask[]
  titleOverrides?: Record<string, string>
  assigneeDirectory?: PortalUserShort[]
  highlightTaskId?: string | null
  showColumnAddButton?: boolean
  /** Ключ sessionStorage для горизонтального scroll (задачи / специалисты). */
  kanbanScrollStorageKey?: string
  onSpecialistDropped?: (specialistSub: string, columnStatus: string) => void
  canDeleteTask?: (task: PortalTask) => boolean
  onDeleteTask?: (taskId: string) => void
  /** Если не передано — drag разрешён для всех карточек (кроме isUpdating). */
  canEditTask?: (task: PortalTask) => boolean
  /** Доска сама прокручивается к первой колонке с задачами (например, при фильтре просрочки). */
  scrollToFirstNonEmptyColumn?: boolean
  exportFilters?: KanbanColumnExportFilters
}) {
  const columnModel = useKanbanColumnModel(columns, boardPref ?? null, tasks, showAllHiddenColumns)

  const resolvedModel = useMemo(() => {
    if (statusOrderOverride !== undefined && getTasksForStatus !== undefined) {
      return {
        statusOrder: statusOrderOverride,
        tasksForStatus: getTasksForStatus,
        titleOverrides: titleOverrides ?? {},
        subtasksFlat: boardPref?.subtasks_flat ?? false,
        hideSubtasks: boardPref?.hide_subtasks ?? false,
      }
    }
    return {
      statusOrder: columnModel.statusOrder,
      tasksForStatus: columnModel.tasksForStatus,
      titleOverrides: { ...columnModel.titleOverrides, ...(titleOverrides ?? {}) },
      subtasksFlat: columnModel.subtasksFlat,
      hideSubtasks: columnModel.hideSubtasks,
    }
  }, [
    statusOrderOverride,
    getTasksForStatus,
    titleOverrides,
    columnModel,
    boardPref?.subtasks_flat,
    boardPref?.hide_subtasks,
  ])

  const statusOrder = resolvedModel.statusOrder
  const taskById = useMemo(() => new Map(tasks.map((t) => [t.id, t])), [tasks])
  const tasksInColumn = useCallback(
    (status: string): PortalTask[] => resolvedModel.tasksForStatus(status),
    [resolvedModel],
  )
  const itemCountByStatus = useMemo(() => {
    const counts = new Map<string, number>()
    for (const status of statusOrder) {
      counts.set(status, tasksInColumn(status).length)
    }
    return counts
  }, [statusOrder, tasksInColumn])

  const tourAnchorTaskId = useMemo(() => {
    for (const status of statusOrder) {
      const demo = tasksInColumn(status).find((t) => t.is_tour_demo)
      if (demo) return demo.id
    }
    for (const status of statusOrder) {
      const first = tasksInColumn(status)[0]
      if (first) return first.id
    }
    return null
  }, [statusOrder, tasksInColumn])

  const subtaskCountMap = useMemo(() => {
    const total = new Map<string, number>()
    const done = new Map<string, number>()
    for (const t of tasks) {
      if (t.parent_task_id === null) continue
      total.set(t.parent_task_id, (total.get(t.parent_task_id) ?? 0) + 1)
      if (isSubtaskProgressDone(t.status, columns)) {
        done.set(t.parent_task_id, (done.get(t.parent_task_id) ?? 0) + 1)
      }
    }
    return { total, done }
  }, [tasks, columns])

  const subtasksByParentId = useMemo(() => {
    const m = new Map<string, PortalTask[]>()
    for (const t of tasks) {
      if (t.parent_task_id === null) continue
      const arr = m.get(t.parent_task_id) ?? []
      arr.push(t)
      m.set(t.parent_task_id, arr)
    }
    for (const arr of m.values()) {
      arr.sort((a, b) => a.position - b.position)
    }
    return m
  }, [tasks])

  const taskIdsInColumnWithNested = useCallback(
    (status: string): Set<string> => {
      const ids = new Set(tasksInColumn(status).map((t) => t.id))
      for (const root of tasksInColumn(status)) {
        for (const st of subtasksByParentId.get(root.id) ?? []) {
          if (st.status === status) ids.add(st.id)
        }
      }
      return ids
    },
    [subtasksByParentId, tasksInColumn],
  )

  const assigneeBySub = useMemo(() => {
    const m = new Map<string, PortalUserShort>()
    for (const u of assigneeDirectory ?? []) {
      m.set(u.sub, u)
    }
    return m
  }, [assigneeDirectory])

  const boardScrollRef = useRef<HTMLDivElement>(null)
  useKanbanScrollPersist(
    boardScrollRef,
    kanbanScrollStorageKey ?? 'tasks-kanban',
    statusOrder.length > 0,
    !scrollToFirstNonEmptyColumn,
  )

  const focusStatus = useMemo(
    () =>
      scrollToFirstNonEmptyColumn
        ? firstNonEmptyColumnStatus(statusOrder, itemCountByStatus)
        : null,
    [scrollToFirstNonEmptyColumn, statusOrder, itemCountByStatus],
  )
  useEffect(() => {
    if (!focusStatus) return
    const scroll = boardScrollRef.current
    const target = scroll?.querySelector<HTMLElement>(`[data-kanban-status="${CSS.escape(focusStatus)}"]`)
    if (!scroll || !target) return
    const scrollLeft = Math.max(0, target.offsetLeft - scroll.offsetLeft - 8)
    scroll.scrollTo({ left: scrollLeft, behavior: 'smooth' })
  }, [focusStatus])

  const {
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
  } = useTaskKanbanDnd({
    statusOrder,
    columns,
    tasks,
    tasksInColumn,
    taskById,
    subtasksByParentId,
    subtasksFlat: resolvedModel.subtasksFlat,
    titleOverrides: resolvedModel.titleOverrides,
    taskIdsInColumnWithNested,
    boardScrollRef,
    onReorder,
    onReorderColumns,
  })

  useInertialWheelScroll(boardScrollRef, !dragScrollActive)
  const pan = useKanbanBoardPointerPan(boardScrollRef, [
    '[data-kanban-card]',
    `.${columnStyles.kanbanColumnHeader}`,
    'button',
    'input, textarea, select',
    `.${columnStyles.addColumnCard}`,
  ])

  return (
    <DndContext
      sensors={sensors}
      autoScroll={kanbanDndAutoScroll}
      collisionDetection={collisionDetection}
      onDragStart={handleDragStart}
      onDragMove={handleDragMove}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
      onDragCancel={handleDragCancel}
    >
      <div
        ref={boardScrollRef}
        className={[boardStyles.kanbanBoardScroll, pan.boardPanning ? boardStyles.kanbanBoardScrollPanning : '']
          .filter(Boolean)
          .join(' ')}
        onPointerDown={pan.onPointerDown}
        onPointerMove={pan.onPointerMove}
        onPointerUp={pan.onPointerUp}
        onPointerCancel={pan.onPointerUp}
        onPointerLeave={pan.onPointerLeave}
      >
        <SortableContext items={statusOrder} strategy={horizontalListSortingStrategy}>
          {statusOrder.map((status) => {
            const colTasks = tasksInColumn(status)
            return (
              <KanbanColumn
                key={status}
                status={status}
                columns={columns}
                canEditColumns={canEditColumns}
                canEditKpi={canEditKpi}
                allowPersonalColumnDrag={allowPersonalColumnDrag}
                titleOverrides={resolvedModel.titleOverrides}
                dropSide={getDropSide(status)}
                onUpdateColumn={onUpdateColumn}
                onDeleteColumn={onDeleteColumn}
                onCreateTask={onCreateTask}
                onOpenCreateModal={onOpenCreateModal}
                onOpenTask={onOpenTask}
                showColumnAddButton={showColumnAddButton}
                onSpecialistDropped={onSpecialistDropped}
                itemCount={colTasks.length}
                exportFilters={exportFilters}
                isDropHidden={isKanbanColumnDropHidden(status, settlingColumnId, unfoldingColumnId)}
                isUnfolding={unfoldingColumnId === status}
              >
                <SortableContext items={colTasks.map((t) => t.id)} strategy={verticalListSortingStrategy}>
                  {colTasks.map((task) => {
                    const nested =
                      resolvedModel.hideSubtasks || resolvedModel.subtasksFlat
                        ? { inColumn: [] as PortalTask[], otherColumns: [] as PortalTask[] }
                        : partitionParentSubtasks(subtasksByParentId.get(task.id) ?? [], status)
                    return (
                      <KanbanCard
                        key={task.id}
                        task={task}
                        parentTask={task.parent_task_id ? (taskById.get(task.parent_task_id) ?? null) : null}
                        subtasksInColumn={nested.inColumn}
                        subtasksOtherColumns={nested.otherColumns}
                        columns={columns}
                        titleOverrides={resolvedModel.titleOverrides}
                        subtaskTotal={subtaskCountMap.total.get(task.id) ?? 0}
                        subtaskDone={subtaskCountMap.done.get(task.id) ?? 0}
                        disabled={(canEditTask ? !canEditTask(task) : false) || isUpdating}
                        showStatusInMeta={status === KANBAN_OTHER_BUCKET}
                        suppressNavAfterDragRef={suppressNavAfterDragRef}
                        assigneeBySub={assigneeBySub}
                        isHighlighted={highlightTaskId === task.id}
                        onOpenTaskDetail={onOpenTaskDetail}
                        canDeleteTask={canDeleteTask?.(task) ?? false}
                        onDeleteTask={onDeleteTask}
                        isTourAnchor={task.id === tourAnchorTaskId}
                      />
                    )
                  })}
                </SortableContext>
              </KanbanColumn>
            )
          })}
        </SortableContext>
        {canEditColumns && onCreateColumn && (
          <AddColumnCard
            canEditKpi={canEditKpi}
            onAdd={(data) => onCreateColumn({ ...data, position: columns.length })}
          />
        )}
      </div>
      {/* Карточки: null — иначе useDropAnimation зовёт scrollIntoView. Колонки: overlay долетает в слот. */}
      <DragOverlay dropAnimation={columnDropAnimation}>
        {activeTask ? (
          <KanbanDragOverlay task={activeTask} assigneeBySub={assigneeBySub} />
        ) : columnOverlay ? (
          <KanbanColumnDragOverlay
            title={columnOverlay.title}
            color={columnOverlay.color}
            itemCount={columnOverlay.itemCount}
            width={columnOverlay.width}
          />
        ) : null}
      </DragOverlay>
    </DndContext>
  )
}
