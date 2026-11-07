import styles from '@/styles/modules/tasks/TasksPageKanbanColumns.module.css'
import dndStyles from '@/styles/modules/tasks/TasksPageKanbanColumnDnd.module.css'

export function KanbanColumnDragOverlay({
  title,
  color,
  itemCount,
  width,
}: {
  title: string
  color: string
  itemCount?: number
  width: number
}) {
  return (
    <div
      className={`${styles.kanbanColumn} ${dndStyles.kanbanColumnDragOverlay}`}
      style={{ borderTopColor: color, width }}
    >
      <div className={styles.kanbanColumnHeader}>
        <span className={styles.kanbanColumnGrip} aria-hidden>
          ⋮⋮
        </span>
        <div className={styles.kanbanColumnTitleGroup}>
          <span className={styles.kanbanColumnTitle} title={title}>
            {title}
          </span>
          {itemCount != null ? (
            <span className={styles.kanbanColumnCount} aria-hidden>
              {itemCount}
            </span>
          ) : null}
        </div>
      </div>
      <div className={`${styles.kanbanColumnBody} ${dndStyles.kanbanColumnDragOverlayBody}`} />
    </div>
  )
}
