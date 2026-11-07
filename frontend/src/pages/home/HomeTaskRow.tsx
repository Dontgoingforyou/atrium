import { Link } from 'react-router'
import { UserAvatar } from '../../components/ui/UserAvatar'
import { usePortalUserDirectory } from '../../hooks/usePortalUserDirectory'
import type { PortalTask, PortalTaskColumn } from '../../types/task'
import { getTaskColumnColor, getTaskColumnTitle, isTaskOverdue } from '../../domain/tasks/taskColumns'
import styles from '@/styles/modules/home/HomePage.module.css'
import { homeDashboardNavState, type TaskBackNavState } from '../tasks/taskBackNav'
import { buildTasksPageUrlWithTask } from '../tasks/tasksPageUrl'

export function HomeTaskRow({
  task,
  columns,
  navState,
}: {
  task: PortalTask
  columns: PortalTaskColumn[]
  navState?: TaskBackNavState
}) {
  const { getAvatarProps } = usePortalUserDirectory()
  const isOverdue = isTaskOverdue(task, columns)
  const statusColor = getTaskColumnColor(task.status, columns)

  const assigneeSub = task.assignee_subs?.[0] ?? task.assignee_sub
  const assignee = assigneeSub ? getAvatarProps(assigneeSub) : null

  return (
    <Link
      to={buildTasksPageUrlWithTask(task.id)}
      state={navState ?? homeDashboardNavState()}
      className={`${styles.taskRow}${isOverdue ? ` ${styles.taskRowOverdue}` : ''}`}
    >
      <span
        className={styles.statusDot}
        style={{ background: statusColor }}
        title={getTaskColumnTitle(task.status, columns)}
      />
      <span className={styles.taskRowTitle}>{task.title}</span>
      <span className={styles.taskRowStatus} style={{ color: statusColor }}>
        {getTaskColumnTitle(task.status, columns)}
      </span>
      {assignee ? (
        <span className={styles.taskRowAssignee} title={assignee.label}>
          <UserAvatar
            label={assignee.label}
            imageUrl={assignee.imageUrl}
            focalX={assignee.focalX}
            focalY={assignee.focalY}
            size="sm"
          />
        </span>
      ) : null}
      {task.due_at ? (
        <span className={`${styles.taskRowDue} ${isOverdue ? styles.taskRowDueOverdue : styles.taskRowDueNormal}`}>
          до {new Date(task.due_at).toLocaleDateString('ru-RU')}
        </span>
      ) : null}
    </Link>
  )
}
