import {
  useMemo,
  useId,
  useState,
  type MutableRefObject,
} from 'react'
import { Link, useLocation, useNavigate } from 'react-router'
import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'

import type { PortalTask, PortalTaskColumn, TaskPriority, TaskStatus } from '../../../types/task'
import { assigneeSubsFromTask } from '../../../domain/tasks/assigneeSubsFromTask'
import { isTaskOverdue } from '../../../domain/tasks/taskColumns'
import { PRIORITY_COLOR, PRIORITY_LABELS, STATUS_LABELS } from '../../../domain/tasks/taskUi'
import type { PortalUserShort } from '../../../api/usersApi'
import { useKanbanTaskNavHandlers } from '../../../pages/tasks/useKanbanTaskNavHandlers'
import { buildTaskOpenNavState } from '../../../pages/tasks/taskBackNav'
import { htmlToPlainTextExcerpt } from '../../../utils/html/richTextPlainText'
import { TaskTagChips } from '../TaskTagChips'
import { KanbanAssigneeAvatars } from './KanbanAssigneeAvatars'
import { KanbanAssigneeAvatar } from './KanbanCardParts'
import { KanbanCardContextMenu } from './KanbanCardContextMenu'
import { KanbanParentStackCard, type KanbanCardShellProps } from './KanbanParentStackCard'
import { IconDotsThreeVertical, IconFileText } from '../../icons/portalIcons'
import cardStyles from '@/styles/modules/tasks/TasksPageKanbanCards.module.css'
import stackStyles from '@/styles/modules/tasks/TasksPageKanbanParentStack.module.css'

export { KanbanAssigneeAvatar }

export function KanbanCard({
  task,
  parentTask,
  subtasksInColumn,
  subtasksOtherColumns = [],
  columns = [],
  titleOverrides,
  subtaskTotal,
  subtaskDone,
  disabled,
  showStatusInMeta,
  suppressNavAfterDragRef,
  assigneeBySub,
  isHighlighted,
  onOpenTaskDetail,
  canDeleteTask = false,
  onDeleteTask,
  isTourAnchor = false,
}: {
  task: PortalTask
  parentTask?: PortalTask | null
  subtasksInColumn: PortalTask[]
  subtasksOtherColumns?: PortalTask[]
  columns?: PortalTaskColumn[]
  titleOverrides?: Record<string, string>
  subtaskTotal: number
  subtaskDone: number
  disabled: boolean
  showStatusInMeta?: boolean
  suppressNavAfterDragRef: MutableRefObject<string | null>
  assigneeBySub: Map<string, PortalUserShort>
  isHighlighted?: boolean
  onOpenTaskDetail?: (taskId: string) => void
  canDeleteTask?: boolean
  onDeleteTask?: (taskId: string) => void
  /** Первая карточка доски — якорь шага онбординга. */
  isTourAnchor?: boolean
}) {
  const subtaskAriaLabelId = useId()
  const parentAriaDescId = useId()

  const assigneeSubs = useMemo(() => assigneeSubsFromTask(task), [task])

  const [ctxMenu, setCtxMenu] = useState<{ x: number; y: number } | null>(null)

  function handleContextMenu(e: React.MouseEvent) {
    e.preventDefault()
    e.stopPropagation()
    setCtxMenu({ x: e.clientX, y: e.clientY })
  }

  const { handleTitleClick, handleBodyClick, navState } = useKanbanTaskNavHandlers(
    task.id,
    suppressNavAfterDragRef,
    onOpenTaskDetail,
  )

  const navigate = useNavigate()
  const location = useLocation()

  function openTaskFromMenu() {
    setCtxMenu(null)
    if (onOpenTaskDetail) {
      onOpenTaskDetail(task.id)
      return
    }
    navigate(`/tasks/${task.id}`, { state: buildTaskOpenNavState(location) })
  }

  const contextMenuEl = ctxMenu ? (
    <KanbanCardContextMenu
      position={ctxMenu}
      canDelete={canDeleteTask && Boolean(onDeleteTask)}
      onClose={() => setCtxMenu(null)}
      onOpen={openTaskFromMenu}
      onDelete={() => onDeleteTask?.(task.id)}
    />
  ) : null

  const descriptionExcerpt = useMemo(
    () => htmlToPlainTextExcerpt(task.description),
    [task.description],
  )

  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: task.id,
    disabled,
    data: { task, type: 'task' },
  })

  const isOverdue = isTaskOverdue(task, columns)

  const nestedSubtasks = subtasksInColumn.length > 0 || subtasksOtherColumns.length > 0

  const cardShellProps: KanbanCardShellProps = {
    ref: setNodeRef,
    'data-kanban-card': true,
    'data-task-id': task.id,
    ...(isTourAnchor ? { 'data-tour': 'tasks-kanban-card' as const } : {}),
    style: {
      // При isDragging оригинал скрыт (placeholder) — движущийся клон рисует DragOverlay.
      // Неактивным карточкам стратегия выдаёт transform для анимации смещения;
      // активной карточке transform не нужен — её rect должен оставаться на месте для collision.
      transform: isDragging ? undefined : (transform ? CSS.Transform.toString(transform) : undefined),
      transition: isDragging ? 'none' : transition,
      opacity: isDragging ? 0 : 1,
      cursor: disabled ? 'default' : nestedSubtasks ? 'default' : isDragging ? 'grabbing' : 'grab',
    },
  }

  if (nestedSubtasks) {
    return (
      <>
        <KanbanParentStackCard
          task={task}
          cardShellProps={cardShellProps}
          listeners={listeners}
          attributes={attributes}
          navState={navState}
          isDragging={isDragging}
          disabled={disabled}
          isHighlighted={isHighlighted}
          assigneeBySub={assigneeBySub}
          subtasksInColumn={subtasksInColumn}
          subtasksOtherColumns={subtasksOtherColumns}
          columns={columns}
          titleOverrides={titleOverrides}
          suppressNavAfterDragRef={suppressNavAfterDragRef}
          onOpenTaskDetail={onOpenTaskDetail}
          showStatusInMeta={showStatusInMeta}
          isOverdue={isOverdue}
          subtaskTotal={subtaskTotal}
          subtaskDone={subtaskDone}
          descriptionExcerpt={descriptionExcerpt}
          onContextMenu={handleContextMenu}
          onTitleClick={handleTitleClick}
          onBodyClick={handleBodyClick}
        />
        {contextMenuEl}
      </>
    )
  }

  if (parentTask) {
    const p = task.priority as TaskPriority
    return (
      <>
      <div
        {...cardShellProps}
        className={[stackStyles.kanbanSubtaskCard, isHighlighted ? cardStyles.kanbanCardHighlight : '']
          .filter(Boolean)
          .join(' ')}
        {...listeners}
        {...attributes}
        role="group"
        aria-labelledby={subtaskAriaLabelId}
        aria-describedby={parentAriaDescId}
        onContextMenu={handleContextMenu}
      >
        <Link
          id={parentAriaDescId}
          to={`/tasks/${parentTask.id}`}
          state={navState}
          className={cardStyles.kanbanStandaloneParentLink}
          aria-label={`Родительская задача: ${parentTask.title}`}
          onPointerDown={(e) => e.stopPropagation()}
          onClick={(e) => {
            e.stopPropagation()
          }}
        >
          ↑ {parentTask.title}
        </Link>
        <Link
          id={subtaskAriaLabelId}
          to={`/tasks/${task.id}`}
          state={navState}
          className={stackStyles.kanbanSubtaskCardLink}
          title={`Открыть подзадачу: ${task.title}`}
          style={{ pointerEvents: isDragging ? 'none' : undefined }}
          onClick={(e) => {
            if (suppressNavAfterDragRef.current === task.id) {
              e.preventDefault()
              suppressNavAfterDragRef.current = null
              return
            }
          }}
        >
          <div className={stackStyles.kanbanSubtaskCardTop}>
            <span className={stackStyles.kanbanSubtaskCardRef}>#{task.number ?? '?'}</span>
            <KanbanAssigneeAvatar
              assigneeSub={task.assignee_sub}
              user={task.assignee_sub ? assigneeBySub.get(task.assignee_sub) : undefined}
            />
          </div>
          <span className={stackStyles.kanbanSubtaskCardTitle}>{task.title}</span>
          <div className={stackStyles.kanbanSubtaskCardFooter}>
            <span className={stackStyles.kanbanSubtaskTypeIcon} aria-hidden title="Подзадача">
              ⧉
            </span>
            <span
              className={stackStyles.kanbanSubtaskPriorityBars}
              title={PRIORITY_LABELS[p] ?? task.priority}
              aria-label={PRIORITY_LABELS[p] ?? task.priority}
            >
              <span style={{ background: PRIORITY_COLOR[p] ?? 'var(--color-border)' }} />
              <span style={{ background: PRIORITY_COLOR[p] ?? 'var(--color-border)' }} />
            </span>
            <span className={stackStyles.kanbanNestedSubtaskOpenCue} aria-hidden>
              Открыть →
            </span>
          </div>
        </Link>
      </div>
      {contextMenuEl}
      </>
    )
  }

  return (
    <>
    <div
      {...cardShellProps}
      className={[cardStyles.kanbanCard, isHighlighted ? cardStyles.kanbanCardHighlight : '']
        .filter(Boolean)
        .join(' ')}
      {...listeners}
      {...attributes}
      onClick={(e) => {
        // Кнопки и ссылки обрабатывают клик сами; остальная поверхность карточки — навигация
        if ((e.target as HTMLElement).closest('a, button')) return
        handleBodyClick(e)
      }}
      onContextMenu={handleContextMenu}
    >
      <div className={cardStyles.kanbanCardTopRow}>
        <span className={cardStyles.kanbanCardRef}>#{task.number ?? '?'}</span>
        <div className={cardStyles.kanbanCardTopRight}>
          <KanbanAssigneeAvatars assigneeSubs={assigneeSubs} assigneeBySub={assigneeBySub} />
          <button
            type="button"
            className={cardStyles.kanbanCardMenuBtn}
            data-tour-hover-action
            aria-label="Действия с задачей"
            onPointerDown={(e) => e.stopPropagation()}
            onClick={(e) => {
              e.stopPropagation()
              e.preventDefault()
              setCtxMenu({ x: e.clientX, y: e.clientY })
            }}
          >
            <IconDotsThreeVertical />
          </button>
        </div>
      </div>
      <div
        className={cardStyles.kanbanCardLink}
        style={{ pointerEvents: isDragging ? 'none' : undefined }}
      >
        <Link
          to={`/tasks/${task.id}`}
          state={navState}
          className={cardStyles.kanbanCardTitleLink}
          onClick={(e) => { e.stopPropagation(); handleTitleClick(e) }}
        >
          <span className={cardStyles.kanbanCardTitle}>{task.title}</span>
        </Link>
        {task.tags.length > 0 ? (
          <div className={cardStyles.kanbanCardTags}>
            <TaskTagChips tags={task.tags} />
          </div>
        ) : null}
        {task.description ? (
          <p className={cardStyles.kanbanCardDesc}>{descriptionExcerpt}</p>
        ) : null}
        <div className={cardStyles.kanbanCardFooter}>
          <div className={cardStyles.kanbanCardMeta}>
            {showStatusInMeta ? (
              <span className={cardStyles.kanbanCardMetaStatus}>
                {STATUS_LABELS[task.status as TaskStatus] ?? task.status}
              </span>
            ) : null}
            {task.due_at ? (
              <span className={isOverdue ? cardStyles.kanbanOverdue : undefined}>
                до {new Date(task.due_at).toLocaleDateString('ru-RU')}
              </span>
            ) : null}
          </div>
          {task.document_title ? (
            <div className={cardStyles.kanbanDocumentBadge} title={`Документ: ${task.document_title}`}>
              <IconFileText size={14} /> {task.document_title}
            </div>
          ) : null}
          {subtaskTotal > 0 && (
            <div className={cardStyles.kanbanSubtaskBadge}>
              {subtaskDone}/{subtaskTotal}
              {subtaskDone > 0 ? ' ✓' : ''}
            </div>
          )}
        </div>
      </div>
    </div>
    {contextMenuEl}
    </>
  )
}
