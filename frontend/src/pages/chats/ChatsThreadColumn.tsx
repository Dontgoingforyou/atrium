import { useCallback, useRef, useState } from 'react'
import type { UseMutationResult } from '@tanstack/react-query'

import { ChatAttachmentsGalleryModal } from '../../components/chat/composer/ChatAttachmentsGalleryModal'
import { ChatEphemeralRows } from '../../components/chat/common/ChatEphemeralRows'
import { ChatHeaderOverflowMenu } from '../../components/chat/thread/ChatHeaderOverflowMenu'
import type { MessageInputHandle } from '../../components/chat/composer/MessageInput'
import type { EphemeralPeer } from '@/utils/chat/chatEphemeral'
import type { useEmojiPongOnline } from '@/hooks/useEmojiPongOnline'
import { ChatMessageList } from '../../components/chat/thread/ChatMessageList'
import { MessageInput } from '../../components/chat/composer/MessageInput'
import { PinnedMessagesBar } from '../../components/chat/thread/PinnedMessagesBar'
import { PresenceInline } from '../../components/chat/common/PresenceInline'
import { IconVolumeOff, IconVolumeOn } from '../../components/icons/VolumeNotificationIcons'
import { IconPaperclip } from '../../components/icons/portalIcons'
import { UserAvatar } from '../../components/ui/UserAvatar'
import type { Chat, ChatMessage, PortalUser, UserPresence } from '../../types/chat'
import {
  getDmChatNotificationSoundEnabled,
} from '@/utils/chat/dmChatNotificationSoundSettings'
import { dmPeerSub } from '@/utils/chat/dmPeerSub'
import { resolveChatAvatarImageUrl } from '@/utils/chat/resolveChatAvatarImageUrl'
import { buildOptimisticReplyPreview } from '@/utils/chat/replyPreview'
import { useChatThreadFileDrop } from './useChatThreadFileDrop'
import styles from '@/styles/modules/chat/ChatsPageThread.module.css'

type SendVars = {
  chatId: string
  body: string
  attachmentIds: string[]
  replyMid?: string | null
  replyQuoteText?: string | null
  replyPreview?: ChatMessage['reply_to']
  mentions?: string[]
}

type Props = {
  /** Ключ react-query списка сообщений этой колонки (совпадает с кэшем мутаций). */
  portalMessagesQueryKey?: readonly unknown[]
  activeChatId: string
  activeTitle: string
  activeChat: Chat | undefined
  activeDmPeerSub: string | null
  mentionUsers: PortalUser[]
  messages: ChatMessage[]
  messagesError?: string | null
  currentUserSub: string | null
  userMap: Record<string, string>
  userAvatarBySub: Record<string, string | undefined>
  avatarFocalBySub: Record<string, { x: number; y: number } | undefined>
  presenceBySub: Record<string, UserPresence>
  lastSeenBySub: Record<string, string | null>
  sortedChats: Chat[]
  deepLinkMessageId: string | null
  stripMessageFromUrl: () => void
  wsDeleteExitRowId?: string | null
  hideOpenChatsLink?: boolean
  onBackToList?: () => void
  replyTo: ChatMessage | null
  replyQuoteText: string | null
  clearReply: () => void
  onReply: (message: ChatMessage, quoteText?: string) => void
  sendMutation: UseMutationResult<ChatMessage, Error, SendVars, unknown>
  onAfterForward: (targetId: string) => void
  handleDmSoundClick: (e: React.MouseEvent, chatId: string) => void
  openSettings: () => void
  ephemeralPeers?: EphemeralPeer[]
  notifyEphemeral?: (event: 'typing' | 'voice_recording', active: boolean) => void
  emojiPong?: ReturnType<typeof useEmojiPongOnline> | null
}

export function ChatsThreadColumn({
  portalMessagesQueryKey,
  activeChatId,
  activeTitle,
  activeChat,
  activeDmPeerSub,
  mentionUsers,
  messages,
  messagesError = null,
  currentUserSub,
  userMap,
  userAvatarBySub,
  avatarFocalBySub,
  presenceBySub,
  lastSeenBySub,
  sortedChats,
  deepLinkMessageId,
  stripMessageFromUrl,
  wsDeleteExitRowId = null,
  hideOpenChatsLink = false,
  onBackToList,
  replyTo,
  replyQuoteText,
  clearReply,
  onReply,
  sendMutation,
  onAfterForward,
  handleDmSoundClick,
  openSettings,
  ephemeralPeers = [],
  notifyEphemeral,
  emojiPong = null,
}: Props) {
  const detailSoundOn = getDmChatNotificationSoundEnabled(activeChatId)
  const messageInputRef = useRef<MessageInputHandle>(null)
  const fileDrop = useChatThreadFileDrop(messageInputRef, sendMutation.isPending)
  const [jumpMessageId, setJumpMessageId] = useState<string | null>(null)
  const [galleryOpen, setGalleryOpen] = useState(false)
  // Сброс при смене чата — во время рендера (React docs: «Adjusting state when a prop
  // changes»), без эффекта, чтобы не ловить react-hooks/set-state-in-effect.
  const [prevChatId, setPrevChatId] = useState(activeChatId)
  if (activeChatId !== prevChatId) {
    setPrevChatId(activeChatId)
    setJumpMessageId(null)
    setGalleryOpen(false)
  }

  const onDeepLinkScrollConsumed = useCallback(() => {
    if (jumpMessageId) {
      setJumpMessageId(null)
    } else {
      stripMessageFromUrl()
    }
  }, [jumpMessageId, stripMessageFromUrl])

  return (
    <>
      <div className={styles.detailHeader} data-tour="chats-thread-header">
        {onBackToList ? (
          <button
            type="button"
            className={styles.threadBackBtn}
            onClick={onBackToList}
            aria-label="Назад к списку чатов"
            title="Назад к списку чатов"
          >
            ‹
          </button>
        ) : null}
        <UserAvatar
          size={40}
          label={activeTitle}
          imageUrl={resolveChatAvatarImageUrl({
            isDirect: Boolean(activeChat?.is_direct),
            peerSub: activeDmPeerSub,
            userAvatarBySub,
            chatAvatarUrl: activeChat?.avatar_url,
          })}
          focalX={
            activeDmPeerSub
              ? avatarFocalBySub[activeDmPeerSub]?.x
              : (activeChat?.avatar_focal_x ?? undefined)
          }
          focalY={
            activeDmPeerSub
              ? avatarFocalBySub[activeDmPeerSub]?.y
              : (activeChat?.avatar_focal_y ?? undefined)
          }
          className={styles.detailHeaderAvatarWrap}
          onClick={() => {
            if (activeChat && !activeChat.is_direct) {
              openSettings()
              return
            }
            setGalleryOpen(true)
          }}
          title={
            activeChat && !activeChat.is_direct ? 'Настройки чата' : 'Вложения чата'
          }
        />
        <div className={styles.detailHeaderTitleBlock}>
          <div className={styles.detailTitleRow}>
            <button
              type="button"
              className={styles.detailTitle}
              onClick={() => {
                if (activeChat && !activeChat.is_direct) {
                  openSettings()
                  return
                }
                setGalleryOpen(true)
              }}
              title={
                activeChat && !activeChat.is_direct ? 'Настройки чата' : 'Вложения чата'
              }
            >
              {activeTitle}
            </button>
            {activeDmPeerSub ? (
              <PresenceInline
                presence={presenceBySub[activeDmPeerSub]}
                lastSeenAt={lastSeenBySub[activeDmPeerSub]}
              />
            ) : null}
          </div>
        </div>
        <div className={styles.detailHeaderActions}>
          <button
            type="button"
            className={styles.soundBtn}
            onClick={(e) => handleDmSoundClick(e, activeChatId)}
            title={
              detailSoundOn
                ? 'Выключить звук уведомлений для этого чата'
                : 'Включить звук уведомлений для этого чата'
            }
            aria-pressed={detailSoundOn}
            aria-label={
              detailSoundOn
                ? 'Звук уведомлений для чата включён'
                : 'Звук уведомлений для чата выключен'
            }
          >
            {detailSoundOn ? <IconVolumeOn /> : <IconVolumeOff />}
          </button>
          <button
            type="button"
            className={styles.attachmentsBtn}
            onClick={() => setGalleryOpen(true)}
            title="Вложения"
            aria-label="Вложения чата"
          >
            <IconPaperclip />
          </button>
          <ChatHeaderOverflowMenu
            chatId={activeChatId}
            showOpenInChats={!hideOpenChatsLink}
            onOpenSettings={!activeChat?.is_direct ? openSettings : undefined}
          />
        </div>
      </div>
      <div
        className={`${styles.messages}${fileDrop.dragOver ? ` ${styles.messagesDragOver}` : ''}`}
        onDragOver={fileDrop.onDragOver}
        onDragLeave={fileDrop.onDragLeave}
        onDrop={fileDrop.onDrop}
      >
        <div className={styles.threadColumn}>
          <PinnedMessagesBar
            chatId={activeChatId}
            userMap={userMap}
            onJumpToMessage={setJumpMessageId}
          />
          {messagesError ? (
            <p className={styles.detailPlaceholder}>{messagesError}</p>
          ) : (
          <ChatMessageList
            chatId={activeChatId}
            messagesQueryKey={portalMessagesQueryKey}
            messages={messages}
            currentUserSub={currentUserSub}
            userMap={userMap}
            userAvatarBySub={userAvatarBySub}
            threadLayout
            scrollToMessageId={jumpMessageId ?? deepLinkMessageId}
            onDeepLinkScrollConsumed={onDeepLinkScrollConsumed}
            onReply={onReply}
            chatsForForward={sortedChats.filter((c) => c.id !== activeChatId)}
            onAfterForward={onAfterForward}
            wsDeleteExitRowId={wsDeleteExitRowId}
            highlightedMessageId={jumpMessageId ?? deepLinkMessageId}
            isDirect={Boolean(activeChat?.is_direct)}
            peerUserSub={activeChat ? dmPeerSub(activeChat, currentUserSub) : null}
            emojiPong={emojiPong}
          />
          )}
          <ChatEphemeralRows peers={ephemeralPeers} userAvatarBySub={userAvatarBySub} />
          <div className={styles.composerWrap} data-tour="chats-composer">
            <MessageInput
              ref={messageInputRef}
              variant="panel"
              chatId={activeChatId}
              mentionUsers={mentionUsers}
              replyTarget={replyTo}
              replyQuoteText={replyQuoteText}
              onClearReply={clearReply}
              onEphemeralActivity={notifyEphemeral}
              onSend={async (body, attachmentIds, replyMid, mentions, quote) => {
                await sendMutation.mutateAsync({
                  chatId: activeChatId,
                  body,
                  attachmentIds,
                  replyMid,
                  replyQuoteText: quote,
                  replyPreview: buildOptimisticReplyPreview(replyTo, replyMid, quote),
                  mentions,
                })
              }}
            />
          </div>
        </div>
      </div>
      <ChatAttachmentsGalleryModal
        open={galleryOpen}
        chatId={activeChatId}
        onClose={() => setGalleryOpen(false)}
        onJumpToMessage={setJumpMessageId}
      />
    </>
  )
}
