import { useRef } from 'react'

import type { Chat, ChatMessage, PortalUser } from '../../../types/chat'
import type { EphemeralPeer } from '@/utils/chat/chatEphemeral'
import type { useEmojiPongOnline } from '@/hooks/useEmojiPongOnline'
import { useChatThreadFileDrop } from '../../../pages/chats/useChatThreadFileDrop'
import { ChatEphemeralRows } from '../common/ChatEphemeralRows'
import { ChatMessageList } from '../thread/ChatMessageList'
import { MessageInput, type MessageInputHandle } from '../composer/MessageInput'
import { PinnedMessagesBar } from '../thread/PinnedMessagesBar'
import styles from '@/styles/modules/chat/FloatingDmWidgetPicker.module.css'

type Props = {
  activeChatId: string
  messages: ChatMessage[]
  currentUserSub: string | null
  userMap: Record<string, string>
  userAvatarBySub?: Record<string, string | undefined>
  ephemeralPeers?: EphemeralPeer[]
  replyTo: ChatMessage | null
  replyQuoteText?: string | null
  sortedChats: Chat[]
  mentionUsers: PortalUser[]
  sendPending: boolean
  onReply: (msg: ChatMessage, quoteText?: string) => void
  onClearReply: () => void
  onEphemeralActivity?: (event: 'typing' | 'voice_recording', active: boolean) => void
  onSend: (
    body: string,
    attachmentIds: string[],
    replyMid?: string | null,
    mentions?: string[],
    replyQuoteText?: string | null,
  ) => Promise<void>
  onAfterForward: (targetId: string) => void
  onChatActivity?: () => void
  /** Диплинк-скролл к сообщению (из PinnedMessagesBar или галереи вложений в хедере попапа). */
  jumpMessageId?: string | null
  onJumpToMessage: (messageId: string | null) => void
  /** Личный диалог. */
  isDirect?: boolean
  /** Собеседник в DM (для шапки счёта в игре). */
  peerUserSub?: string | null
  emojiPong?: ReturnType<typeof useEmojiPongOnline> | null
}

export function ActiveChatPanel({
  activeChatId,
  messages,
  currentUserSub,
  userMap,
  userAvatarBySub,
  ephemeralPeers = [],
  replyTo,
  replyQuoteText = null,
  sortedChats,
  mentionUsers,
  sendPending,
  onReply,
  onClearReply,
  onEphemeralActivity,
  onSend,
  onAfterForward,
  onChatActivity,
  jumpMessageId = null,
  onJumpToMessage,
  isDirect = false,
  peerUserSub = null,
  emojiPong = null,
}: Props) {
  const messageInputRef = useRef<MessageInputHandle>(null)
  const fileDrop = useChatThreadFileDrop(messageInputRef, sendPending)

  return (
    <div
      className={`${styles.messages}${fileDrop.dragOver ? ` ${styles.messagesDragOver}` : ''}`}
      onDragOver={fileDrop.onDragOver}
      onDragLeave={fileDrop.onDragLeave}
      onDrop={fileDrop.onDrop}
      onMouseMove={onChatActivity}
    >
      <PinnedMessagesBar chatId={activeChatId} userMap={userMap} onJumpToMessage={onJumpToMessage} />
      <ChatMessageList
        chatId={activeChatId}
        messages={messages}
        currentUserSub={currentUserSub}
        userMap={userMap}
        userAvatarBySub={userAvatarBySub}
        onReply={onReply}
        chatsForForward={sortedChats.filter((c) => c.id !== activeChatId)}
        onAfterForward={onAfterForward}
        scrollToMessageId={jumpMessageId}
        onDeepLinkScrollConsumed={() => onJumpToMessage(null)}
        highlightedMessageId={jumpMessageId}
        isDirect={isDirect}
        peerUserSub={peerUserSub}
        emojiPong={emojiPong}
      />
      <ChatEphemeralRows peers={ephemeralPeers} userAvatarBySub={userAvatarBySub} />
      <MessageInput
        ref={messageInputRef}
        chatId={activeChatId}
        mentionUsers={mentionUsers}
        replyTarget={replyTo}
        replyQuoteText={replyQuoteText}
        onClearReply={onClearReply}
        onEphemeralActivity={onEphemeralActivity}
        onSend={onSend}
        disabled={sendPending}
        variant="widget"
      />
    </div>
  )
}
