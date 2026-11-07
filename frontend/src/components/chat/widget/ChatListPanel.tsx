import type { Chat, UserPresence } from '../../../types/chat'
import styles from '@/styles/modules/chat/FloatingDmWidgetChrome.module.css'
import { OpenChatsPageLink } from './OpenChatsPageLink'
import { PortalChatListRows, type PortalChatListRowsClasses } from '../common/PortalChatListRows'

const chatListClasses: PortalChatListRowsClasses = {
  list: styles.list,
  listEmpty: styles.listEmpty,
  rowOuter: styles.dmRow,
  rowOuterActive: '',
  rowButton: styles.dmItem,
  avatar: styles.chatListAvatar,
  chatNameBlock: styles.chatNameBlock,
  chatName: styles.chatName,
  chatPresenceLine: styles.chatPresenceLine,
  chatMeta: styles.chatMeta,
  unreadPill: styles.unreadPill,
  soundBtn: styles.dmRowSoundBtn,
}

type Props = {
  sortedChats: Chat[]
  currentUserSub: string | null
  userMap: Record<string, string>
  userAvatarBySub?: Record<string, string | undefined>
  presenceBySub: Record<string, UserPresence>
  lastSeenBySub: Record<string, string | null>
  avatarFocalBySub: Record<string, { x: number; y: number } | undefined>
  dmNotifTick: number
  onChatOpen: (chatId: string) => void
  onDmSoundClick: (e: React.MouseEvent, chatId: string) => void
  onNewDm: () => void
  onNewGroup: () => void
  onOpenFullscreen?: () => void
  onChatRowContextMenu?: (e: React.MouseEvent, chat: Chat) => void
}

export function ChatListPanel({
  sortedChats,
  currentUserSub,
  userMap,
  userAvatarBySub = {},
  presenceBySub,
  lastSeenBySub,
  avatarFocalBySub,
  dmNotifTick,
  onChatOpen,
  onDmSoundClick,
  onNewDm,
  onNewGroup,
  onOpenFullscreen,
  onChatRowContextMenu,
}: Props) {
  return (
    <>
      <PortalChatListRows
        sortedChats={sortedChats}
        currentUserSub={currentUserSub}
        userMap={userMap}
        userAvatarBySub={userAvatarBySub}
        presenceBySub={presenceBySub}
        lastSeenBySub={lastSeenBySub}
        avatarFocalBySub={avatarFocalBySub}
        dmNotifTick={dmNotifTick}
        classes={chatListClasses}
        onChatOpen={onChatOpen}
        onDmSoundClick={onDmSoundClick}
        onChatRowContextMenu={onChatRowContextMenu}
      />
      <div className={styles.footer}>
        <OpenChatsPageLink
          className={`${styles.openChatsLink} ${styles.footerOpenChats}`}
          onNavigate={onOpenFullscreen}
        />
        <div className={styles.footerActions}>
          <button type="button" className={styles.newDmBtn} onClick={onNewDm}>
            + Диалог
          </button>
          <button type="button" className={styles.newGroupBtn} onClick={onNewGroup}>
            + Группа
          </button>
        </div>
      </div>
    </>
  )
}
