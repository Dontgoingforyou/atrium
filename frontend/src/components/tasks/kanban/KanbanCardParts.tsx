import type { MutableRefObject } from 'react'
import { Link, useLocation } from 'react-router'
import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'

import type { PortalTask, PortalTaskColumn, TaskPriority } from '../../../types/task'
import { PRIORITY_COLOR, PRIORITY_LABELS } from '../../../domain/tasks/taskUi'
import { getTaskColumnTitle } from '../../../domain/tasks/taskColumns'
import type { PortalUserShort } from '../../../api/usersApi'
import { getUserDisplayLabel } from '../../../utils/userLabel'
import { buildTaskOpenNavState } from '../../../pages/tasks/taskBackNav'
import { UserAvatar } from '../../ui/UserAvatar'
import { TaskTagChips } from '../TaskTagChips'
import styles from '@/styles/modules/tasks/TasksPageKanbanParentStack.module.css'

export function KanbanAssigneeAvatar({
  assigneeSub,
  user,
  showFallback = true,
}: {
  assigneeSub: string | null
  user?: PortalUserShort | undefined
  showFallback?: boolean
}) {
  if (!assigneeSub && !showFallback) return null
  const label = getUserDisplayLabel(
    {
      sub: assigneeSub || '?',
      display_name: user?.display_name,
      email: user?.email,
      username: user?.username,
    },
    { trim: true },
  )
  return (
    <UserAvatar
      label={label}
      imageUrl={user?.avatar_url}
      focalX={user?.avatar_focal_x}
      focalY={user?.avatar_focal_y}
      size="sm"
      className={styles.kanbanSubtaskAssigneeAvatar}
      title={label}
    />
  )
}

export function KanbanSubtaskCard({
  task,
  assigneeUser,
  suppressNavAfterDragRef,
  disabled,
  onOpenTaskDetail,
}: {
  task: PortalTask
  assigneeUser?: PortalUserShort | undefined
  suppressNavAfterDragRef: MutableRefObject<string | null>
  disabled: boolean
  onOpenTaskDetail?: (taskId: string) => void
}) {
  const p = task.priority as TaskPriority
  const location = useLocation()
  const navState = buildTaskOpenNavState(location)

  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: task.id,
    disabled,
    data: { task, type: 'task' },
  })

  return (
    <div
      ref={setNodeRef}
      className={styles.kanbanSubtaskCard}
      data-kanban-subtask
      data-task-id={task.id}
      aria-label={`Подзадача: ${task.title}`}
      style={{
        transform: isDragging ? undefined : (transform ? CSS.Transform.toString(transform) : undefined),
        transition: isDragging ? 'none' : transition,
        opacity: isDragging ? 0 : 1,
        cursor: disabled ? 'default' : isDragging ? 'grabbing' : 'grab',
      }}
      {...listeners}
      {...attributes}
    >
      <Link
        to={`/tasks/${task.id}`}
        state={navState}
        className={styles.kanbanSubtaskCardLink}
        title={`Открыть подзадачу: ${task.title}`}
        style={{ pointerEvents: isDragging ? 'none' : undefined }}
        onClick={(e) => {
          if (suppressNavAfterDragRef.current === task.id) {
            e.preventDefault()
            suppressNavAfterDragRef.current = null
            return
          }
          if (onOpenTaskDetail && !e.ctrlKey && !e.metaKey && !e.shiftKey) {
            e.preventDefault()
            onOpenTaskDetail(task.id)
          }
        }}
      >
        <div className={styles.kanbanSubtaskCardTop}>
          <span className={styles.kanbanSubtaskKindBadge}>Подзадача</span>
          <span className={styles.kanbanSubtaskCardRef}>#{task.number ?? '?'}</span>
          <KanbanAssigneeAvatar assigneeSub={task.assignee_sub} user={assigneeUser} />
        </div>
        <span className={styles.kanbanSubtaskCardTitle}>{task.title}</span>
        {task.tags.length > 0 ? (
          <div className={styles.kanbanSubtaskCardTags}>
            <TaskTagChips tags={task.tags} />
          </div>
        ) : null}
        <div className={styles.kanbanSubtaskCardFooter}>
          <span className={styles.kanbanSubtaskTypeIcon} aria-hidden title="Подзадача">
            ⧉
          </span>
          <span
            className={styles.kanbanSubtaskPriorityBars}
            title={PRIORITY_LABELS[p] ?? task.priority}
            aria-label={PRIORITY_LABELS[p] ?? task.priority}
          >
            <span style={{ background: PRIORITY_COLOR[p] ?? 'var(--color-border)' }} />
            <span style={{ background: PRIORITY_COLOR[p] ?? 'var(--color-border)' }} />
          </span>
          <span className={styles.kanbanNestedSubtaskOpenCue} aria-hidden>
            Открыть →
          </span>
        </div>
      </Link>
    </div>
  )
}

/** Подзадача в другом статусе — только ссылка (DnD остаётся в колонке её статуса). */
export function KanbanOtherStatusSubtaskRow({
  task,
  columns,
  titleOverrides,
  assigneeUser,
  onOpenTaskDetail,
}: {
  task: PortalTask
  columns: PortalTaskColumn[]
  titleOverrides?: Record<string, string>
  assigneeUser?: PortalUserShort | undefined
  onOpenTaskDetail?: (taskId: string) => void
}) {
  const location = useLocation()
  const navState = buildTaskOpenNavState(location)
  const statusLabel = getTaskColumnTitle(task.status, columns, titleOverrides)

  return (
    <div
      className={styles.kanbanOtherStatusSubtask}
      data-kanban-subtask-other
      data-task-id={task.id}
    >
      <Link
        to={`/tasks/${task.id}`}
        state={navState}
        className={styles.kanbanOtherStatusSubtaskLink}
        title={`Открыть подзадачу: ${task.title}`}
        onClick={(e) => {
          if (onOpenTaskDetail && !e.ctrlKey && !e.metaKey && !e.shiftKey) {
            e.preventDefault()
            onOpenTaskDetail(task.id)
          }
        }}
      >
        <div className={styles.kanbanOtherStatusSubtaskTop}>
          <span className={styles.kanbanSubtaskKindBadge}>Подзадача</span>
          <span className={styles.kanbanSubtaskCardRef}>#{task.number ?? '?'}</span>
          <span className={styles.kanbanOtherStatusBadge} title={statusLabel}>
            {statusLabel}
          </span>
          <KanbanAssigneeAvatar assigneeSub={task.assignee_sub} user={assigneeUser} />
        </div>
        <span className={styles.kanbanSubtaskCardTitle}>{task.title}</span>
        <div className={styles.kanbanSubtaskCardFooter}>
          <span className={styles.kanbanNestedSubtaskOpenCue} aria-hidden>
            Открыть →
          </span>
        </div>
      </Link>
    </div>
  )
}
