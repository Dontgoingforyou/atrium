import { useEffect, useId, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router'
import type { PortalTask, PortalTaskColumn } from '../../types/task'
import { KanbanAssigneeAvatars } from './kanban/KanbanAssigneeAvatars'
import { usePortalUserDirectory } from '../../hooks/usePortalUserDirectory'
import { useClickOutside } from '../../hooks/useClickOutside'
import { htmlToPlainTextExcerpt } from '../../utils/html/richTextPlainText'
import { assigneeSubsFromTask } from '../../domain/tasks/assigneeSubsFromTask'
import {
  buildTaskStatusSelectOptions,
  getTaskColumnColor,
  getTaskColumnTitle,
  isTaskOverdue,
} from '../../domain/tasks/taskColumns'
import { PRIORITY_LABELS } from '../../domain/tasks/taskUi'
import { TaskTagChips } from './TaskTagChips'
import styles from '@/styles/modules/tasks/TasksPageTaskRow.module.css'

export function TaskRow({
  task,
  columns,
  onStatusChange,
  isUpdating,
  canEdit = true,
  isSubtask = false,
  navState,
}: {
  task: PortalTask
  columns: PortalTaskColumn[]
  onStatusChange: (s: string) => void
  isUpdating: boolean
  canEdit?: boolean
  isSubtask?: boolean
  navState?: { from?: string; tasksReturnTo?: string }
}) {
  const { bySub } = usePortalUserDirectory()
  const assigneeSubs = useMemo(() => assigneeSubsFromTask(task), [task])

  const [statusMenuOpen, setStatusMenuOpen] = useState(false)
  const [statusActiveIndex, setStatusActiveIndex] = useState<number>(-1)
  const statusMenuWrapRef = useRef<HTMLSpanElement>(null)
  const statusTriggerRef = useRef<HTMLButtonElement>(null)
  const statusItemRefs = useRef<Array<HTMLButtonElement | null>>([])
  const statusMenuId = useId()

  const statusOptions = useMemo(
    () => buildTaskStatusSelectOptions(columns, task.status),
    [columns, task.status],
  )
  const statusColor = getTaskColumnColor(task.status, columns)
  const statusLabel = getTaskColumnTitle(task.status, columns)
  const isOverdue = isTaskOverdue(task, columns)

  function closeStatusMenu() {
    setStatusMenuOpen(false)
    setStatusActiveIndex(-1)
  }

  function openStatusMenu() {
    setStatusMenuOpen(true)
    setStatusActiveIndex(statusOptions.length > 0 ? 0 : -1)
  }

  useClickOutside(statusMenuOpen, [statusMenuWrapRef], closeStatusMenu)

  useEffect(() => {
    if (statusActiveIndex < 0) return
    const el = statusItemRefs.current[statusActiveIndex]
    el?.scrollIntoView({ block: 'nearest' })
  }, [statusActiveIndex])

  function selectStatus(value: string) {
    closeStatusMenu()
    onStatusChange(value)
  }

  function onStatusTriggerKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault()
      if (!statusMenuOpen) {
        openStatusMenu()
        return
      }
      const dir = e.key === 'ArrowDown' ? 1 : -1
      setStatusActiveIndex((i) => {
        const n = statusOptions.length
        if (n === 0) return i
        return (i + dir + n) % n
      })
    } else if (e.key === 'Enter' || e.key === ' ') {
      if (statusMenuOpen && statusActiveIndex >= 0) {
        e.preventDefault()
        selectStatus(statusOptions[statusActiveIndex].value)
      }
    } else if (e.key === 'Escape') {
      if (statusMenuOpen) {
        e.preventDefault()
        closeStatusMenu()
        statusTriggerRef.current?.focus()
      }
    }
  }

  const descriptionExcerpt = useMemo(
    () => htmlToPlainTextExcerpt(task.description),
    [task.description],
  )

  return (
    <div
      className={`row-card ${styles.taskRowCard} ${isSubtask ? styles.taskRowCardSubtask : ''}`}
      style={{ borderColor: isOverdue ? 'var(--color-danger-ui)' : undefined }}
    >
      <div className={styles.taskRowBody}>
        <div className={styles.taskRowTitleBlock}>
          {isSubtask ? (
            <span className={styles.taskRowSubtaskBadge} aria-label="Подзадача">
              ⧉ Подзадача
            </span>
          ) : null}
          <Link to={`/tasks/${task.id}`} state={navState} className={styles.taskRowTitleLink}>
            {task.title}
          </Link>
          {task.tags.length > 0 ? (
            <div className={styles.taskRowFooterTags}>
              <TaskTagChips tags={task.tags} />
            </div>
          ) : null}
          <span className={styles.taskRowPriority}>{PRIORITY_LABELS[task.priority]}</span>
          <time className={styles.taskRowDate} dateTime={task.created_at}>
            {new Date(task.created_at).toLocaleDateString('ru-RU')}
          </time>
          {task.due_at ? (
            <time
              className={`${styles.taskRowDate} ${isOverdue ? styles.taskRowDateOverdue : ''}`}
              dateTime={task.due_at}
            >
              до {new Date(task.due_at).toLocaleDateString('ru-RU')}
            </time>
          ) : null}
        </div>
        {descriptionExcerpt ? (
          <p className={styles.taskRowDescription}>{descriptionExcerpt}</p>
        ) : null}
        <div className={styles.taskRowBottom}>
          <div className={styles.taskRowMeta}>
            {assigneeSubs.length > 0 ? (
              <KanbanAssigneeAvatars assigneeSubs={assigneeSubs} assigneeBySub={bySub} />
            ) : null}
          </div>
          <div className={styles.taskRowFooter}>
            <span className={styles.statusSelectWrap} ref={statusMenuWrapRef}>
              <button
                ref={statusTriggerRef}
                type="button"
                disabled={isUpdating || !canEdit}
                onClick={() => (statusMenuOpen ? closeStatusMenu() : openStatusMenu())}
                onKeyDown={onStatusTriggerKeyDown}
                className={styles.statusSelect}
                style={{
                  border: `1px solid ${statusColor}`,
                  color: statusColor,
                }}
                aria-haspopup="menu"
                aria-expanded={statusMenuOpen}
                aria-controls={statusMenuId}
                aria-activedescendant={
                  statusMenuOpen && statusActiveIndex >= 0
                    ? `${statusMenuId}-opt-${statusActiveIndex}`
                    : undefined
                }
              >
                {statusLabel}
                <span className={styles.statusSelectArrow} aria-hidden>
                  ⇕
                </span>
              </button>
              {statusMenuOpen ? (
                <div className={styles.statusMenu} role="menu" id={statusMenuId} aria-label="Статус задачи">
                  {statusOptions.map((opt, idx) => (
                    <button
                      key={opt.value}
                      ref={(el) => { statusItemRefs.current[idx] = el }}
                      id={`${statusMenuId}-opt-${idx}`}
                      type="button"
                      role="menuitem"
                      className={styles.statusMenuItem}
                      style={{ color: opt.color }}
                      data-active={idx === statusActiveIndex ? 'true' : undefined}
                      onMouseEnter={() => setStatusActiveIndex(idx)}
                      onClick={() => selectStatus(opt.value)}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              ) : null}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
