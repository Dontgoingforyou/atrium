import type { Chat, ChatMessage } from '../../../types/chat'

import type { AudienceAnchorRect } from '@/utils/chat/audiencePopoverPos'
import type { useEmojiPongOnline } from '@/hooks/useEmojiPongOnline'

export type CtxEmojiPicker = {
  messageId: string
  anchorTop: number
  anchorBottom: number
  anchorLeft: number
}

export type ReadersPopover = {
  messageId: string
  anchorRect: AudienceAnchorRect
}

export type ReactorsPopover = {
  messageId: string
  emoji: string
  anchorRect: AudienceAnchorRect
}

export type ChatMessageListProps = {
  chatId: string
  /** Полный ключ react-query списка сообщений (страница /chats — с суффиксом wide|default). */
  messagesQueryKey?: readonly unknown[]
  messages: ChatMessage[]
  currentUserSub: string | null
  userMap?: Record<string, string>
  userAvatarBySub?: Record<string, string | undefined>
  threadLayout?: boolean
  onReply?: (message: ChatMessage, quoteText?: string) => void
  chatsForForward?: Chat[]
  onAfterForward?: (targetChatId: string) => void
  scrollToMessageId?: string | null
  onDeepLinkScrollConsumed?: () => void
  /** id строки сообщения, анимирующейся перед удалением по WS-событию у других пользователей. */
  wsDeleteExitRowId?: string | null
  /** id сообщения, которое нужно подсветить (deeplink из пуш-уведомления). */
  highlightedMessageId?: string | null
  /** Личный диалог — пасхалка emoji-catch и шаринг счёта. */
  isDirect?: boolean
  /** Собеседник в DM (для шапки счёта). */
  peerUserSub?: string | null
  /** Онлайн emoji-pong (WS), только DM. */
  emojiPong?: ReturnType<typeof useEmojiPongOnline> | null
}
