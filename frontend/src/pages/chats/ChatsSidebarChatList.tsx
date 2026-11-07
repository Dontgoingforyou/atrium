import type { Chat, UserPresence } from '../../types/chat'
import { PortalChatListRows, type PortalChatListRowsClasses } from '../../components/chat/common/PortalChatListRows'
import sidebar from '@/styles/modules/chat/ChatsPageSidebar.module.css'
import thread from '@/styles/modules/chat/ChatsPageThread.module.css'

const pageChatListClasses: PortalChatListRowsClasses = {
  list: sidebar.list,
  listEmpty: sidebar.listEmpty,
  rowOuter: sidebar.chatRowWrap,
  rowOuterActive: sidebar.chatRowWrapActive,
  rowButton: sidebar.chatRow,
  avatar: thread.chatRowAvatar,
  chatNameBlock: sidebar.chatNameBlock,
  chatName: sidebar.chatName,
  chatPresenceLine: sidebar.chatPresenceLine,
  chatMeta: sidebar.chatMeta,
  unreadPill: sidebar.unreadPill,
  soundCell: sidebar.soundCell,
  soundBtn: thread.soundBtn,
}

type Props = {
  sortedChats: Chat[]
  listError?: string | null
  currentUserSub: string | null
  userMap: Record<string, string>
  userAvatarBySub: Record<string, string | undefined>
  presenceBySub: Record<string, UserPresence>
  lastSeenBySub: Record<string, string | null>
  avatarFocalBySub: Record<string, { x: number; y: number } | undefined>
  dmNotifTick: number
  activeChatId: string | null
  onChatOpen: (chatId: string) => void
  onDmSoundClick: (e: React.MouseEvent, chatId: string) => void
  onChatRowContextMenu: (e: React.MouseEvent, chat: Chat) => void
}

export function ChatsSidebarChatList({ listError, ...props }: Props) {
  if (listError) {
    return <p className={sidebar.listEmpty}>{listError}</p>
  }
  return (
    <PortalChatListRows
      {...props}
      classes={pageChatListClasses}
    />
  )
}
