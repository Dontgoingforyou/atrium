import type { PortalNotification } from '../../types/notification'
import type { TaskPriority, TaskStatus } from '../../types/task'
import { calendarEventDetailsLine, notificationEntityLabel, notificationPrimaryLine } from '../../domain/notifications/notificationLabels'
import { PRIORITY_LABELS, STATUS_LABELS } from '../../domain/tasks/taskUi'
import { formatMskDate } from '../../utils/time/formatMskDate'
import { UserAvatar } from '../ui/UserAvatar'
import styles from '@/styles/modules/layout/MentionNotificationsBell.module.css'

function assignmentDetailsLine(n: PortalNotification): string {
  if (n.type !== 'task_assigned' && n.type !== 'task_due_soon' && n.type !== 'task_overdue') {
    return ''
  }
  const parts: string[] = []
  if (n.task_priority) {
    const p = n.task_priority as TaskPriority
    if (p in PRIORITY_LABELS) {
      parts.push(`приоритет: ${PRIORITY_LABELS[p]}`)
    } else {
      parts.push(`приоритет: ${n.task_priority}`)
    }
  }
  if (n.task_due_at) {
    parts.push(`срок: ${formatMskDate(n.task_due_at)}`)
  }
  if (n.task_status) {
    const s = n.task_status as TaskStatus
    if (s in STATUS_LABELS) {
      parts.push(`статус: ${STATUS_LABELS[s]}`)
    } else {
      parts.push(`статус: ${n.task_status}`)
    }
  }
  return parts.join(' · ')
}

function formatTimeAgo(isoString: string): string {
  const diffMs = Date.now() - new Date(isoString).getTime()
  const diffMin = Math.floor(diffMs / 60_000)
  if (diffMin < 1) return 'только что'
  if (diffMin < 60) return `${diffMin} мин. назад`
  const diffH = Math.floor(diffMin / 60)
  if (diffH < 24) return `${diffH} ч. назад`
  const diffD = Math.floor(diffH / 24)
  return `${diffD} д. назад`
}

export function NotificationItemRow({
  notif,
  onItemClick,
  onDelete,
  deletePending,
}: {
  notif: PortalNotification
  onItemClick: (n: PortalNotification) => void
  onDelete: (id: string) => void
  deletePending: boolean
}) {
  const assignmentMeta = assignmentDetailsLine(notif)
  const calendarMeta = calendarEventDetailsLine(notif)
  const metaLine = assignmentMeta || calendarMeta
  return (
    <div key={notif.id} className={styles.itemRow}>
      <div className={styles.itemAvatarCell}>
        <UserAvatar
          size={36}
          label={notif.author_display_name ?? notif.author_sub}
          imageUrl={notif.author_avatar_url ?? undefined}
        />
      </div>
      <button
        type="button"
        className={
          notif.read_at != null ? `${styles.item} ${styles.itemRead}` : styles.item
        }
        onClick={() => onItemClick(notif)}
      >
        <span className={styles.itemAuthor}>{notificationPrimaryLine(notif)}</span>
        <span className={styles.itemTask}>{notificationEntityLabel(notif)}</span>
        {metaLine ? <span className={styles.itemMeta}>{metaLine}</span> : null}
        <span className={styles.itemTime}>{formatTimeAgo(notif.created_at)}</span>
      </button>
      <button
        type="button"
        className={styles.itemDismiss}
        onClick={(e) => {
          e.stopPropagation()
          onDelete(notif.id)
        }}
        disabled={deletePending}
        title="Удалить"
        aria-label="Удалить уведомление"
      >
        ×
      </button>
    </div>
  )
}
