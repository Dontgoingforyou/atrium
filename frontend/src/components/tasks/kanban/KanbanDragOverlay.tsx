import { useMemo } from 'react'

import type { PortalTask, TaskPriority } from '../../../types/task'
import type { PortalUserShort } from '../../../api/usersApi'
import { assigneeSubsFromTask } from '../../../domain/tasks/assigneeSubsFromTask'
import { PRIORITY_COLOR, PRIORITY_LABELS } from '../../../domain/tasks/taskUi'
import { htmlToPlainTextExcerpt } from '../../../utils/html/richTextPlainText'
import { KanbanAssigneeAvatars } from './KanbanAssigneeAvatars'
import { KanbanAssigneeAvatar } from './KanbanCardParts'
import { TaskTagChips } from '../TaskTagChips'
import cardStyles from '@/styles/modules/tasks/TasksPageKanbanCards.module.css'
import stackStyles from '@/styles/modules/tasks/TasksPageKanbanParentStack.module.css'

/**
 * Визуальный превью карточки, отображаемый поверх всего во время перетаскивания (DragOverlay).
 * Только для чтения — без интерактивных элементов.
 */
export function KanbanDragOverlay({
  task,
  assigneeBySub,
}: {
  task: PortalTask
  assigneeBySub: Map<string, PortalUserShort>
}) {
  const descriptionExcerpt = useMemo(
    () => htmlToPlainTextExcerpt(task.description),
    [task.description],
  )

  if (task.parent_task_id) {
    const p = task.priority as TaskPriority
    return (
      <div className={`${stackStyles.kanbanSubtaskCard} ${cardStyles.kanbanDragOverlayCard}`}>
        <div className={stackStyles.kanbanSubtaskCardTop}>
          <span className={stackStyles.kanbanSubtaskCardRef}>#{task.number ?? '?'}</span>
          <KanbanAssigneeAvatar
            assigneeSub={task.assignee_sub}
            user={task.assignee_sub ? assigneeBySub.get(task.assignee_sub) : undefined}
          />
        </div>
        <span className={stackStyles.kanbanSubtaskCardTitle}>{task.title}</span>
        <div className={stackStyles.kanbanSubtaskCardFooter}>
          <span className={stackStyles.kanbanSubtaskTypeIcon} aria-hidden>
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
        </div>
      </div>
    )
  }

  const assigneeSubs = assigneeSubsFromTask(task)

  return (
    <div className={`${cardStyles.kanbanCard} ${cardStyles.kanbanDragOverlayCard}`}>
      <div className={cardStyles.kanbanCardTopRow}>
        <span className={cardStyles.kanbanCardRef}>#{task.number ?? '?'}</span>
        <div className={cardStyles.kanbanCardTopRight}>
          <KanbanAssigneeAvatars assigneeSubs={assigneeSubs} assigneeBySub={assigneeBySub} />
        </div>
      </div>
      <div className={cardStyles.kanbanCardLink}>
        <span className={cardStyles.kanbanCardTitle}>{task.title}</span>
        {task.tags.length > 0 ? (
          <div className={cardStyles.kanbanCardTags}>
            <TaskTagChips tags={task.tags} />
          </div>
        ) : null}
        {task.description ? (
          <p className={cardStyles.kanbanCardDesc}>{descriptionExcerpt}</p>
        ) : null}
      </div>
    </div>
  )
}
