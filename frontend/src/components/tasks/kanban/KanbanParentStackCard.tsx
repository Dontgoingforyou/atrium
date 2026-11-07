import { useState, type CSSProperties } from 'react'
import { Link } from 'react-router'
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable'
import type { DraggableAttributes, DraggableSyntheticListeners } from '@dnd-kit/core'

import type { PortalTask, PortalTaskColumn, TaskStatus } from '../../../types/task'
import { STATUS_LABELS } from '../../../domain/tasks/taskUi'
import type { PortalUserShort } from '../../../api/usersApi'
import type { TaskBackNavState } from '../../../pages/tasks/taskBackNav'
import { TaskTagChips } from '../TaskTagChips'
import { KanbanAssigneeAvatar, KanbanOtherStatusSubtaskRow, KanbanSubtaskCard } from './KanbanCardParts'
import cardStyles from '@/styles/modules/tasks/TasksPageKanbanCards.module.css'
import stackStyles from '@/styles/modules/tasks/TasksPageKanbanParentStack.module.css'

export type KanbanCardShellProps = {
  ref: (el: HTMLDivElement | null) => void
  'data-kanban-card': true
  'data-task-id': string
  'data-tour'?: 'tasks-kanban-card'
  style: CSSProperties
}

type Props = {
  task: PortalTask
  cardShellProps: KanbanCardShellProps
  listeners: DraggableSyntheticListeners
  attributes: DraggableAttributes
  navState: TaskBackNavState | undefined
  isDragging: boolean
  disabled: boolean
  isHighlighted?: boolean
  assigneeBySub: Map<string, PortalUserShort>
  subtasksInColumn: PortalTask[]
  subtasksOtherColumns: PortalTask[]
  columns: PortalTaskColumn[]
  titleOverrides?: Record<string, string>
  suppressNavAfterDragRef: React.MutableRefObject<string | null>
  onOpenTaskDetail?: (taskId: string) => void
  showStatusInMeta?: boolean
  isOverdue: boolean
  subtaskTotal: number
  subtaskDone: number
  descriptionExcerpt: string
  onContextMenu: (e: React.MouseEvent) => void
  onTitleClick: (e: React.MouseEvent<HTMLAnchorElement>) => void
  onBodyClick: (e: React.MouseEvent<HTMLElement>) => void
}

/** Карточка-родитель со стеком подзадач (вложенные подзадачи в колонке и в других статусах). */
export function KanbanParentStackCard({
  task,
  cardShellProps,
  listeners,
  attributes,
  navState,
  isDragging,
  disabled,
  isHighlighted,
  assigneeBySub,
  subtasksInColumn,
  subtasksOtherColumns,
  columns,
  titleOverrides,
  suppressNavAfterDragRef,
  onOpenTaskDetail,
  showStatusInMeta,
  isOverdue,
  subtaskTotal,
  subtaskDone,
  descriptionExcerpt,
  onContextMenu,
  onTitleClick,
  onBodyClick,
}: Props) {
  const [subtasksCollapsed, setSubtasksCollapsed] = useState(false)
  const nestedSubtaskCount = subtasksInColumn.length + subtasksOtherColumns.length

  return (
    <div
      {...cardShellProps}
      className={[
        cardStyles.kanbanCard,
        stackStyles.kanbanParentStack,
        isHighlighted ? cardStyles.kanbanCardHighlight : '',
      ]
        .filter(Boolean)
        .join(' ')}
      onContextMenu={onContextMenu}
    >
        <div
          className={stackStyles.kanbanParentStackHeader}
          {...listeners}
          {...attributes}
          style={{ cursor: disabled ? 'default' : isDragging ? 'grabbing' : 'grab' }}
          onClick={(e) => {
            if ((e.target as HTMLElement).closest('a, button')) return
            onBodyClick(e)
          }}
        >
          <div className={stackStyles.kanbanParentStackHeaderRow}>
            <span className={cardStyles.kanbanCardRef}>#{task.number ?? '?'}</span>
            <Link
              to={`/tasks/${task.id}`}
              state={navState}
              className={stackStyles.kanbanParentStackTitleLink}
              style={{ pointerEvents: isDragging ? 'none' : undefined }}
              onClick={onTitleClick}
            >
              <span className={stackStyles.kanbanParentStackTitle}>{task.title}</span>
            </Link>
            {task.assignee_sub ? (
              <KanbanAssigneeAvatar
                assigneeSub={task.assignee_sub}
                user={assigneeBySub.get(task.assignee_sub)}
                showFallback={false}
              />
            ) : null}
          </div>
        </div>
        <div
          className={stackStyles.kanbanParentStackSummary}
          style={{ pointerEvents: isDragging ? 'none' : undefined }}
          onClick={(e) => {
            if ((e.target as HTMLElement).closest('a, button')) return
            onBodyClick(e)
          }}
        >
          <div className={`${cardStyles.kanbanCardLink} ${stackStyles.kanbanParentStackSummaryBody}`}>
            {task.tags.length > 0 ? (
              <div className={`${cardStyles.kanbanCardTags} ${stackStyles.kanbanParentStackSummaryTags}`}>
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
              {subtaskTotal > 0 ? (
                <button
                  type="button"
                  className={stackStyles.kanbanSubtaskBadgeBtn}
                  title={subtasksCollapsed ? 'Показать подзадачи' : 'Скрыть подзадачи'}
                  aria-expanded={!subtasksCollapsed}
                  onPointerDown={(e) => e.stopPropagation()}
                  onClick={(e) => {
                    e.stopPropagation()
                    setSubtasksCollapsed((v) => !v)
                  }}
                >
                  {subtaskDone}/{subtaskTotal}
                  {subtaskDone > 0 ? ' ✓' : ''}
                </button>
              ) : null}
            </div>
          </div>
        </div>
        <div className={stackStyles.kanbanParentStackBody}>
          <button
            type="button"
            className={stackStyles.kanbanParentStackSubtasksToggle}
            aria-expanded={!subtasksCollapsed}
            onPointerDown={(e) => e.stopPropagation()}
            onClick={(e) => {
              e.stopPropagation()
              setSubtasksCollapsed((v) => !v)
            }}
          >
            <span
              className={[
                stackStyles.kanbanParentStackSubtasksChevron,
                subtasksCollapsed ? '' : stackStyles.kanbanParentStackSubtasksChevronOpen,
              ]
                .filter(Boolean)
                .join(' ')}
              aria-hidden
            />
            <span>Подзадачи</span>
            <span className={stackStyles.kanbanParentStackSubtasksCount}>
              ({nestedSubtaskCount})
            </span>
            <span className={stackStyles.kanbanParentStackSubtasksAction}>
              {subtasksCollapsed ? 'показать' : 'скрыть'}
            </span>
          </button>
          <div
            className={[
              stackStyles.kanbanParentStackSubtasksPanel,
              subtasksCollapsed ? '' : stackStyles.kanbanParentStackSubtasksPanelOpen,
            ]
              .filter(Boolean)
              .join(' ')}
          >
            <div className={stackStyles.kanbanParentStackSubtasksPanelInner}>
              {subtasksInColumn.length > 0 ? (
                <SortableContext
                  items={subtasksInColumn.map((st) => st.id)}
                  strategy={verticalListSortingStrategy}
                >
                  <div className={stackStyles.kanbanParentStackSubtasksList}>
                    {subtasksInColumn.map((st) => (
                      <KanbanSubtaskCard
                        key={st.id}
                        task={st}
                        assigneeUser={st.assignee_sub ? assigneeBySub.get(st.assignee_sub) : undefined}
                        suppressNavAfterDragRef={suppressNavAfterDragRef}
                        disabled={disabled}
                        onOpenTaskDetail={onOpenTaskDetail}
                      />
                    ))}
                  </div>
                </SortableContext>
              ) : null}
              {subtasksOtherColumns.length > 0 ? (
                <div className={stackStyles.kanbanParentStackSubtasksList}>
                  {subtasksOtherColumns.map((st) => (
                    <KanbanOtherStatusSubtaskRow
                      key={st.id}
                      task={st}
                      columns={columns}
                      titleOverrides={titleOverrides}
                      assigneeUser={st.assignee_sub ? assigneeBySub.get(st.assignee_sub) : undefined}
                      onOpenTaskDetail={onOpenTaskDetail}
                    />
                  ))}
                </div>
              ) : null}
          </div>
        </div>
      </div>
    </div>
  )
}
