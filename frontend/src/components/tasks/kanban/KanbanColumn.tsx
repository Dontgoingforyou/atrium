import { useRef, useState, type CSSProperties } from 'react'
import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'

import { exportTaskColumnTasks } from '../../../api/tasks/tasksApi'
import type { PortalTaskColumn, TaskColumnUpdate } from '../../../types/task'
import { KANBAN_OTHER_BUCKET } from '../../../domain/kanban/kanbanDisplayCommon'
import { getTaskColumnColor, getTaskColumnTitle } from '../../../domain/tasks/taskColumns'
import { useNotifyToast } from '../../../hooks/useNotifyToast'
import { userFacingMessageFromUnknown } from '../../../utils/apiUserMessage'
import { ConfirmDialog } from '../../ui/ConfirmDialog'
import { kanbanColumnAnimateLayoutChanges, KANBAN_COLUMN_UNFOLD_DURATION_MS } from './kanbanDndAnimation'
import { AddColumnCard } from './AddColumnCard'
import { KanbanColumnInlineCreate } from './KanbanColumnInlineCreate'
import { IconDownload, IconPencil, IconPlus, IconX } from '../../icons/portalIcons'
import styles from '@/styles/modules/tasks/TasksPageKanbanColumns.module.css'
import dndStyles from '@/styles/modules/tasks/TasksPageKanbanColumnDnd.module.css'

export { AddColumnCard }

export type KanbanColumnExportFilters = {
  mine_only?: boolean
  assignee_sub?: string[]
}

export function KanbanColumn({
  status,
  columns,
  canEditColumns,
  canEditKpi = false,
  allowPersonalColumnDrag,
  titleOverrides,
  dropSide,
  onUpdateColumn,
  onDeleteColumn,
  onCreateTask,
  onOpenCreateModal,
  onOpenTask,
  showColumnAddButton = true,
  onSpecialistDropped,
  itemCount,
  exportFilters,
  tourHeaderAnchor = 'tasks-kanban-column-header',
  enableExport = true,
  isDropHidden = false,
  isUnfolding = false,
  children,
}: {
  status: string
  columns: PortalTaskColumn[]
  canEditColumns: boolean
  canEditKpi?: boolean
  allowPersonalColumnDrag: boolean
  titleOverrides?: Record<string, string>
  dropSide: 'left' | 'right' | null
  onUpdateColumn?: (id: string, data: TaskColumnUpdate) => void
  onDeleteColumn?: (id: string) => void
  onCreateTask?: (title: string, status: string) => Promise<string>
  onOpenCreateModal?: (status: string) => void
  onOpenTask?: (taskId: string) => void
  showColumnAddButton?: boolean
  onSpecialistDropped?: (specialistSub: string, columnStatus: string) => void
  itemCount?: number
  exportFilters?: KanbanColumnExportFilters
  /** Якорь тура для шапки колонки (задачи / специалисты). */
  tourHeaderAnchor?: string
  /** Выгрузка TXT — только для доски задач. */
  enableExport?: boolean
  /** Скрыть колонку, пока overlay долетает в слот. */
  isDropHidden?: boolean
  /** Разворот после drop компактного превью. */
  isUnfolding?: boolean
  children: React.ReactNode
}) {
  const col = columns.find((c) => c.status_key === status)
  const isOtherBucket = status === KANBAN_OTHER_BUCKET
  const canDragColumnHeader =
    !isOtherBucket && (allowPersonalColumnDrag || (canEditColumns && !!col))
  const showExportBtn = enableExport && Boolean(col) && !isOtherBucket

  const {
    setNodeRef,
    attributes,
    listeners,
    transform,
    transition,
    isDragging,
    isOver,
  } = useSortable({
    id: status,
    disabled: !canDragColumnHeader,
    data: { type: 'column', status },
    animateLayoutChanges: kanbanColumnAnimateLayoutChanges,
  })

  const [isEditing, setIsEditing] = useState(false)
  const [editTitle, setEditTitle] = useState('')
  const [editColor, setEditColor] = useState('')
  const [editExcludeFromKpi, setEditExcludeFromKpi] = useState(false)
  const titleRef = useRef<HTMLInputElement>(null)
  const [isInlineCreateOpen, setIsInlineCreateOpen] = useState(false)
  const [isExporting, setIsExporting] = useState(false)
  const [pendingDelete, setPendingDelete] = useState(false)
  const notify = useNotifyToast()

  function startEdit() {
    setEditTitle(getTaskColumnTitle(status, columns, titleOverrides))
    setEditColor(getTaskColumnColor(status, columns))
    setEditExcludeFromKpi(col?.exclude_from_kpi ?? false)
    setIsEditing(true)
    setTimeout(() => titleRef.current?.focus(), 0)
  }

  function cancelEdit() { setIsEditing(false) }

  function saveEdit() {
    if (!col || !onUpdateColumn) return
    const payload: TaskColumnUpdate = {
      title: editTitle.trim() || undefined,
      color: editColor || undefined,
    }
    if (canEditKpi) {
      payload.exclude_from_kpi = editExcludeFromKpi
    }
    onUpdateColumn(col.id, payload)
    setIsEditing(false)
  }

  function handleDelete() {
    if (!col || !onDeleteColumn) return
    setPendingDelete(true)
  }

  function handleAddTaskClick() {
    if (onCreateTask) {
      setIsInlineCreateOpen(true)
    } else if (onOpenCreateModal) {
      onOpenCreateModal(status)
    }
  }

  async function handleExportClick() {
    if (!col || isExporting) return
    setIsExporting(true)
    try {
      await exportTaskColumnTasks({
        columnId: col.id,
        mine_only: exportFilters?.mine_only,
        assignee_sub: exportFilters?.assignee_sub,
      })
    } catch (e: unknown) {
      notify(userFacingMessageFromUnknown(e))
    } finally {
      setIsExporting(false)
    }
  }

  const topColor = getTaskColumnColor(status, columns)
  const title = getTaskColumnTitle(status, columns, titleOverrides)
  const showColumnDragRegion = canDragColumnHeader && !isEditing
  const showAddBtn = showColumnAddButton && (onCreateTask || onOpenCreateModal) && !isOtherBucket

  const exportButton = showExportBtn ? (
    <button
      type="button"
      className={styles.kanbanExportBtn}
      data-tour-hover-action
      onClick={() => void handleExportClick()}
      title="Выгрузить TXT"
      aria-label="Выгрузить TXT"
      disabled={isExporting}
      onPointerDown={(e) => e.stopPropagation()}
    >
      <IconDownload />
    </button>
  ) : null

  const countBadge =
    itemCount != null ? (
      <span className={styles.kanbanColumnCount} aria-label={`Задач в колонке: ${itemCount}`}>
        {itemCount}
      </span>
    ) : null

  const [specialistDragOver, setSpecialistDragOver] = useState(false)

  function handleDragOver(e: React.DragEvent) {
    if (!onSpecialistDropped || isOtherBucket) return
    const sub = e.dataTransfer.types.includes('specialist-sub')
    if (!sub) return
    e.preventDefault()
    setSpecialistDragOver(true)
  }

  function handleDragLeave() {
    setSpecialistDragOver(false)
  }

  function handleDrop(e: React.DragEvent) {
    setSpecialistDragOver(false)
    if (!onSpecialistDropped || isOtherBucket) return
    const sub = e.dataTransfer.getData('specialist-sub')
    if (!sub) return
    e.preventDefault()
    onSpecialistDropped(sub, status)
  }

  const columnStyle: CSSProperties = {
    transform: transform ? CSS.Transform.toString(transform) : undefined,
    transition,
    opacity: isDragging || isDropHidden ? 0 : 1,
    borderTopColor: topColor,
  }
  if (isUnfolding) {
    columnStyle.animationDuration = `${KANBAN_COLUMN_UNFOLD_DURATION_MS}ms`
  }

  return (
    <>
      <div
        ref={setNodeRef}
      className={`${styles.kanbanColumn} ${dndStyles.kanbanColumnDnd}`}
      data-kanban-status={status}
      data-drag-over={isOver && !isDragging ? 'true' : undefined}
      data-dragging={isDragging ? 'true' : undefined}
      data-drop-hidden={isDropHidden ? 'true' : undefined}
      data-unfolding={isUnfolding ? 'true' : undefined}
      data-drop-left={dropSide === 'left' ? 'true' : undefined}
      data-drop-right={dropSide === 'right' ? 'true' : undefined}
      data-specialist-drag-over={specialistDragOver ? 'true' : undefined}
      style={columnStyle}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div className={styles.kanbanColumnHeader} data-tour={tourHeaderAnchor}>
        {isEditing ? (
          <div className={styles.kanbanColumnEditRow} onPointerDown={(e) => e.stopPropagation()}>
            <input
              ref={titleRef}
              type="text"
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              className={styles.kanbanColumnEditInput}
              aria-label="Название колонки"
              onKeyDown={(e) => {
                if (e.key === 'Enter') saveEdit()
                if (e.key === 'Escape') cancelEdit()
              }}
            />
            <input
              type="color"
              value={editColor}
              onChange={(e) => setEditColor(e.target.value)}
              className={styles.kanbanColumnColorPicker}
              title="Цвет колонки"
            />
            {canEditKpi ? (
              <label
                className={styles.kanbanColumnKpiToggle}
                title="Если включено, задачи в этой колонке не учитываются в KPI «открытых» на главной. При общем status_key с другой колонкой исключается весь ключ."
              >
                <input
                  type="checkbox"
                  checked={editExcludeFromKpi}
                  onChange={(e) => setEditExcludeFromKpi(e.target.checked)}
                  aria-label="Исключить из KPI"
                />
                <span className={`${styles.kanbanColumnKpiToggleLabel} visually-hidden-sm`}>
                  Исключить из KPI
                </span>
              </label>
            ) : null}
            <div className={styles.kanbanColumnEditActions}>
              <button type="button" className={styles.kanbanEditSaveBtn} onClick={saveEdit} title="Сохранить" aria-label="Сохранить">✓</button>
              <button type="button" className={styles.kanbanEditCancelBtn} onClick={cancelEdit} title="Отмена" aria-label="Отмена">
                <IconX />
              </button>
            </div>
          </div>
        ) : showColumnDragRegion ? (
          <>
            <div
              className={[
                styles.kanbanColumnDragRegion,
                isDragging ? styles.kanbanColumnHeaderDragging : '',
              ].filter(Boolean).join(' ')}
              title="Перетащить колонку (порядок только для вас)"
              {...listeners}
              {...attributes}
            >
              <span className={styles.kanbanColumnGrip} aria-hidden>⋮⋮</span>
              <div className={styles.kanbanColumnTitleGroup}>
                <span className={styles.kanbanColumnTitle} title={title}>{title}</span>
                {countBadge}
              </div>
            </div>
            {showAddBtn ? (
              <button
                type="button"
                className={styles.kanbanAddTaskHeaderBtn}
                data-tour-hover-action
                onClick={handleAddTaskClick}
                title="Добавить задачу в колонку"
                aria-label="Добавить задачу в колонку"
                onPointerDown={(e) => e.stopPropagation()}
              >
                <IconPlus />
              </button>
            ) : null}
            {exportButton}
            {canEditColumns && col ? (
              <>
                <button
                  type="button"
                  className={styles.kanbanEditBtn}
                  data-tour-hover-action
                  onClick={startEdit}
                  title="Редактировать колонку"
                  aria-label="Редактировать колонку"
                  onPointerDown={(e) => e.stopPropagation()}
                >
                  <IconPencil />
                </button>
                <button
                  type="button"
                  className={styles.kanbanDeleteBtn}
                  data-tour-hover-action
                  onClick={handleDelete}
                  title="Удалить колонку"
                  aria-label="Удалить колонку"
                  onPointerDown={(e) => e.stopPropagation()}
                >
                  <IconX />
                </button>
              </>
            ) : null}
          </>
        ) : (
          <>
            <div className={styles.kanbanColumnTitleGroup}>
              <span className={styles.kanbanColumnTitle} title={title}>{title}</span>
              {countBadge}
            </div>
            {showAddBtn ? (
              <button
                type="button"
                className={styles.kanbanAddTaskHeaderBtn}
                data-tour-hover-action
                onClick={handleAddTaskClick}
                title="Добавить задачу в колонку"
                aria-label="Добавить задачу в колонку"
                onPointerDown={(e) => e.stopPropagation()}
              >
                <IconPlus />
              </button>
            ) : null}
            {exportButton}
          </>
        )}
      </div>
      <div className={styles.kanbanColumnBody}>
        {onCreateTask && !isOtherBucket && isInlineCreateOpen ? (
          <KanbanColumnInlineCreate
            status={status}
            onCreateTask={onCreateTask}
            onOpenTask={(taskId) => onOpenTask?.(taskId)}
            onClose={() => setIsInlineCreateOpen(false)}
          />
        ) : null}
        {children}
      </div>
    </div>
      {col && onDeleteColumn ? (
        <ConfirmDialog
          open={pendingDelete}
          title="Удалить колонку?"
          message={`Колонка «${col.title}» будет удалена.`}
          confirmLabel="Удалить"
          cancelLabel="Отмена"
          destructive
          onConfirm={() => {
            onDeleteColumn(col.id)
            setPendingDelete(false)
          }}
          onCancel={() => setPendingDelete(false)}
        />
      ) : null}
    </>
  )
}
