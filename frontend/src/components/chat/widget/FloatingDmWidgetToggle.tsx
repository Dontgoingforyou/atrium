import styles from '@/styles/modules/chat/FloatingDmWidgetChrome.module.css'
import { IconChat } from '../../icons/portalIcons'

type Props = {
  totalUnread: number
  onClick: () => void
  expanded?: boolean
}

export function FloatingDmWidgetToggle({ totalUnread, onClick, expanded = false }: Props) {
  return (
    <button
      type="button"
      className={styles.toggleBtn}
      onClick={onClick}
      title={expanded ? 'Свернуть' : 'Сообщения'}
      aria-label={expanded ? 'Свернуть мини-чат' : 'Сообщения'}
    >
      <span className={styles.toggleBtnInner}>
        <IconChat />
        {totalUnread > 0 && (
          <span className={styles.dmUnreadBadge}>
            {totalUnread > 99 ? '99+' : totalUnread}
          </span>
        )}
      </span>
    </button>
  )
}
