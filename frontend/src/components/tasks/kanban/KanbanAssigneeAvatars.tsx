import type { PortalUserShort } from '../../../api/usersApi'
import { getUserDisplayLabel } from '../../../utils/userLabel'
import { KanbanAssigneeAvatar } from './KanbanCardParts'
import styles from '@/styles/modules/tasks/TasksPageKanbanCards.module.css'

const MAX_VISIBLE_ASSIGNEES = 3

type Props = {
  assigneeSubs: string[]
  assigneeBySub: Map<string, PortalUserShort>
}

/** До трёх аватаров исполнителей; при большем числе — «+N». */
export function KanbanAssigneeAvatars({ assigneeSubs, assigneeBySub }: Props) {
  if (assigneeSubs.length === 0) return null

  const visible = assigneeSubs.slice(0, MAX_VISIBLE_ASSIGNEES)
  const extra = assigneeSubs.length - MAX_VISIBLE_ASSIGNEES
  const title = assigneeSubs
    .map((sub) => {
      const u = assigneeBySub.get(sub)
      return getUserDisplayLabel(
        { sub, display_name: u?.display_name, email: u?.email, username: u?.username },
        { trim: true },
      )
    })
    .join(', ')

  return (
    <span className={styles.kanbanAssigneeGroup} title={title}>
      {visible.map((sub) => (
        <KanbanAssigneeAvatar
          key={sub}
          assigneeSub={sub}
          user={assigneeBySub.get(sub)}
          showFallback={false}
        />
      ))}
      {extra > 0 ? <span className={styles.kanbanAssigneeExtra}>+{extra}</span> : null}
    </span>
  )
}
