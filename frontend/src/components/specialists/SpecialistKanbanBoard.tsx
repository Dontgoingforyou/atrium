import { useMemo, useRef } from 'react'
import { DndContext, DragOverlay } from '@dnd-kit/core'
import { SortableContext, horizontalListSortingStrategy, verticalListSortingStrategy } from '@dnd-kit/sortable'

import {
  computeSpecialistKanbanDisplay,
  groupKanbanEntriesBySpecialist,
} from '../../domain/specialists/specialistBoardPref'
import { KANBAN_OTHER_BUCKET } from '../../domain/kanban/kanbanDisplayCommon'
import { getTaskColumnColor, getTaskColumnTitle } from '../../domain/tasks/taskColumns'
import type { KanbanInsertAnchor } from '../../domain/kanban/kanbanDisplayCommon'
import { useInertialWheelScroll } from '../../hooks/useInertialWheelScroll'
import { useKanbanBoardPointerPan } from '../../hooks/useKanbanBoardPointerPan'
import { useKanbanScrollPersist } from '../../hooks/useKanbanScrollPersist'
import type { ManagerSpecialistEntry, SpecialistBoardPref, SpecialistColumn } from '../../types/specialist'
import type { PortalTaskColumn, TaskColumnCreate, TaskColumnUpdate } from '../../types/task'
import { KanbanColumn } from '../tasks/kanban/KanbanColumn'
import { KanbanColumnDragOverlay } from '../tasks/kanban/KanbanColumnDragOverlay'
import { isKanbanColumnDropHidden, useKanbanColumnDropAnimation } from '../tasks/kanban/kanbanDndAnimation'
import { AddColumnCard } from '../tasks/kanban/AddColumnCard'
import { SpecialistKanbanCard } from './SpecialistKanbanCard'
import { SpecialistKanbanDragOverlay } from './SpecialistKanbanDragOverlay'
import { useSpecialistKanbanDnd } from './useSpecialistKanbanDnd'
import styles from '@/styles/modules/tasks/TasksPageKanbanCards.module.css'

const KANBAN_DND_AUTO_SCROLL = { enabled: false, layoutShiftCompensation: false } as const

interface Props {
  columns: SpecialistColumn[]
  /** Упорядоченные ключи колонок (персональный порядок). */
  columnOrder: string[]
  boardPref?: SpecialistBoardPref | null
  showAllHiddenColumns?: boolean
  entries: ManagerSpecialistEntry[]
  onMoveSpecialist: (specialistSub: string, columnKey: string) => void
  onReorderEntry?: (entryId: string, columnKey: string, anchor: KanbanInsertAnchor) => void
  onAddSpecialist?: (columnKey: string) => void
  onRemoveSpecialist: (specialistSub: string) => void
  onCardClick?: (entry: ManagerSpecialistEntry) => void
  onReorderColumns?: (columnKeys: string[]) => void
  /** sub текущего пользователя — карточки других менеджеров только для просмотра. */
  currentUserSub?: string
  /** id записи, для которой идёт PATCH column_key (спиннер селекта). */
  movingEntryId?: string | null
  showColumnAddButton?: boolean
  canAddColumn?: boolean
  onAddColumn?: (data: { key: string; title: string; color: string; position: number }) => void
  canEditColumns?: boolean
  onUpdateColumn?: (id: string, data: TaskColumnUpdate) => void
  onDeleteColumn?: (id: string) => void
  /** В «Все специалисты» — одна карточка на человека, менеджеры через запятую. */
  groupCardsBySpecialist?: boolean
  kanbanScrollStorageKey?: string
}

function toTaskColumn(col: SpecialistColumn): PortalTaskColumn {
  return {
    id: col.id,
    title: col.title,
    color: col.color,
    status_key: col.key,
    position: col.position,
    exclude_from_kpi: false,
  }
}

export function SpecialistKanbanBoard({
  columns,
  columnOrder,
  boardPref = null,
  showAllHiddenColumns = false,
  entries,
  onMoveSpecialist,
  onReorderEntry,
  onAddSpecialist,
  onRemoveSpecialist,
  onCardClick,
  onReorderColumns,
  currentUserSub,
  showColumnAddButton = true,
  canAddColumn = false,
  onAddColumn,
  canEditColumns = false,
  onUpdateColumn,
  onDeleteColumn,
  groupCardsBySpecialist = false,
  kanbanScrollStorageKey,
  movingEntryId = null,
}: Props) {
  const columnByKey = useMemo(() => new Map(columns.map((c) => [c.key, c])), [columns])

  const { displayColumnKeys, entriesForColumn } = useMemo(
    () => computeSpecialistKanbanDisplay(columnOrder, entries, boardPref, showAllHiddenColumns),
    [columnOrder, entries, boardPref, showAllHiddenColumns],
  )

  const displayColumns = useMemo(() => {
    const out: SpecialistColumn[] = []
    for (const key of displayColumnKeys) {
      if (key === KANBAN_OTHER_BUCKET) {
        out.push({
          id: KANBAN_OTHER_BUCKET,
          key: KANBAN_OTHER_BUCKET,
          title: 'Прочие (скрытые колонки)',
          color: 'var(--color-text-disabled)',
          position: 9999,
        })
      } else {
        const col = columnByKey.get(key)
        if (col) out.push(col)
      }
    }
    return out
  }, [displayColumnKeys, columnByKey])

  const tourAnchorEntryId = useMemo(() => {
    for (const key of displayColumnKeys) {
      if (key === KANBAN_OTHER_BUCKET) continue
      const first = entriesForColumn(key)[0]
      if (first) return first.id
    }
    return null
  }, [displayColumnKeys, entriesForColumn])

  const taskColumns: PortalTaskColumn[] = useMemo(
    () => displayColumns.map(toTaskColumn),
    [displayColumns],
  )

  const boardScrollRef = useRef<HTMLDivElement>(null)
  useKanbanScrollPersist(
    boardScrollRef,
    kanbanScrollStorageKey ?? 'specialists-kanban',
    displayColumns.length > 0,
  )

  const allowPersonalColumnDrag = Boolean(onReorderColumns)

  const {
    sensors,
    activeEntry,
    collisionDetection,
    handleDragStart,
    handleDragOver,
    handleDragEnd,
    handleDragCancel,
    getDropSide,
    draggingColumnKey,
    columnOverlayWidth,
  } = useSpecialistKanbanDnd({
    columnOrder,
    displayColumnKeys,
    entries,
    entriesForColumn,
    boardScrollRef,
    onReorderEntry,
    onReorderColumns,
  })

  const {
    dropAnimation: columnDropAnimation,
    settlingColumnId,
    unfoldingColumnId,
    markColumnDragStart,
    markNonColumnDragStart,
    finishColumnDrop,
    cancelColumnDrop,
  } = useKanbanColumnDropAnimation()

  useInertialWheelScroll(boardScrollRef, !activeEntry && !draggingColumnKey)
  const pan = useKanbanBoardPointerPan(boardScrollRef, [
    '[data-kanban-card]',
    'button',
    'input, textarea, select',
  ])

  function isEntryReadOnly(entry: ManagerSpecialistEntry): boolean {
    if (!currentUserSub) return false
    return entry.manager_sub !== currentUserSub
  }

  function handleAddColumn(data: TaskColumnCreate) {
    onAddColumn?.({
      key: data.status_key,
      title: data.title,
      color: data.color ?? '#0f766e',
      position: displayColumns.length,
    })
  }

  return (
    <DndContext
      sensors={sensors}
      autoScroll={KANBAN_DND_AUTO_SCROLL}
      collisionDetection={collisionDetection}
      onDragStart={(event) => {
        if (event.active.data.current?.type === 'column') markColumnDragStart()
        else markNonColumnDragStart()
        handleDragStart(event)
      }}
      onDragOver={handleDragOver}
      onDragEnd={(event) => {
        const columnId =
          event.active.data.current?.type === 'column' &&
          typeof event.active.data.current?.status === 'string'
            ? event.active.data.current.status
            : undefined
        handleDragEnd(event)
        if (columnId) finishColumnDrop(columnId)
        else cancelColumnDrop()
      }}
      onDragCancel={() => {
        handleDragCancel()
        cancelColumnDrop()
      }}
    >
      <div
        ref={boardScrollRef}
        data-tour="specialists-kanban"
        className={[
          styles.kanbanBoardScroll,
          pan.boardPanning ? styles.kanbanBoardScrollPanning : '',
        ]
          .filter(Boolean)
          .join(' ')}
        onPointerDown={pan.onPointerDown}
        onPointerMove={pan.onPointerMove}
        onPointerUp={pan.onPointerUp}
        onPointerCancel={pan.onPointerUp}
        onPointerLeave={pan.onPointerLeave}
      >
        <SortableContext items={displayColumnKeys} strategy={horizontalListSortingStrategy}>
        {displayColumns.map((col) => {
          const colEntries = groupCardsBySpecialist
            ? groupKanbanEntriesBySpecialist(entriesForColumn(col.key), currentUserSub)
            : entriesForColumn(col.key)
          return (
            <KanbanColumn
              key={col.key}
              status={col.key}
              columns={taskColumns}
              canEditColumns={canEditColumns && col.key !== KANBAN_OTHER_BUCKET}
              allowPersonalColumnDrag={allowPersonalColumnDrag && col.key !== KANBAN_OTHER_BUCKET}
              onUpdateColumn={onUpdateColumn}
              onDeleteColumn={onDeleteColumn}
              dropSide={getDropSide(col.key)}
              showColumnAddButton={showColumnAddButton && col.key !== KANBAN_OTHER_BUCKET}
              onOpenCreateModal={onAddSpecialist}
              onSpecialistDropped={
                col.key === KANBAN_OTHER_BUCKET ? undefined : onMoveSpecialist
              }
              itemCount={colEntries.length}
              tourHeaderAnchor="specialists-kanban-column-header"
              enableExport={false}
              isDropHidden={isKanbanColumnDropHidden(col.key, settlingColumnId, unfoldingColumnId)}
              isUnfolding={unfoldingColumnId === col.key}
            >
              <SortableContext
                items={onReorderEntry ? colEntries.map((entry) => entry.id) : []}
                strategy={verticalListSortingStrategy}
              >
                {colEntries.map((entry) => (
                  <SpecialistKanbanCard
                    key={groupCardsBySpecialist ? entry.specialist_sub : entry.id}
                    entry={entry}
                    columns={columns}
                    readOnly={isEntryReadOnly(entry)}
                    sortable={Boolean(onReorderEntry)}
                    onRemove={onRemoveSpecialist}
                    onColumnChange={
                      isEntryReadOnly(entry) ? undefined : onMoveSpecialist
                    }
                    columnChanging={movingEntryId === entry.id}
                    onCardClick={onCardClick}
                    isTourAnchor={entry.id === tourAnchorEntryId}
                  />
                ))}
              </SortableContext>
            </KanbanColumn>
          )
        })}
        </SortableContext>

        {canAddColumn && onAddColumn && <AddColumnCard onAdd={handleAddColumn} />}
      </div>
      <DragOverlay dropAnimation={columnDropAnimation}>
        {activeEntry ? (
          <SpecialistKanbanDragOverlay entry={activeEntry} />
        ) : draggingColumnKey && columnOverlayWidth != null ? (
          <KanbanColumnDragOverlay
            title={getTaskColumnTitle(draggingColumnKey, taskColumns)}
            color={getTaskColumnColor(draggingColumnKey, taskColumns)}
            itemCount={entriesForColumn(draggingColumnKey).length}
            width={columnOverlayWidth}
          />
        ) : null}
      </DragOverlay>
    </DndContext>
  )
}
