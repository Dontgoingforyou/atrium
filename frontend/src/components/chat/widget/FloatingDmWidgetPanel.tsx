import { useState, type Dispatch, type SetStateAction } from 'react'

import type { Chat, ChatMessage, PortalUser, UserPresence } from '../../../types/chat'
import type { useEmojiPongOnline } from '@/hooks/useEmojiPongOnline'
import type { EphemeralPeer } from '@/utils/chat/chatEphemeral'
import { buildOptimisticReplyPreview } from '@/utils/chat/replyPreview'
import { resolveChatAvatarImageUrl } from '@/utils/chat/resolveChatAvatarImageUrl'
import { IconVolumeOff, IconVolumeOn } from '../../icons/VolumeNotificationIcons'
import { IconPaperclip } from '../../icons/portalIcons'
import { UserAvatar } from '../../ui/UserAvatar'
import { ActiveChatPanel } from './ActiveChatPanel'
import { ChatAttachmentsGalleryModal } from '../composer/ChatAttachmentsGalleryModal'
import { ChatHeaderOverflowMenu } from '../thread/ChatHeaderOverflowMenu'
import { ChatListPanel } from './ChatListPanel'
import { CreateGroupPanel } from './CreateGroupPanel'
import { DmPickerPanel } from './DmPickerPanel'
import { PresenceInline } from '../common/PresenceInline'
import styles from '@/styles/modules/chat/FloatingDmWidgetChrome.module.css'

type View = 'list' | 'picker' | 'groupPicker' | 'chat'

export type FloatingDmWidgetPanelProps = {
  view: View
  setView: (v: View) => void
  panelHidden?: boolean
  onMinimize: () => void
  onClosePanel: () => void
  activeChatId: string | null
  activeChat: Chat | undefined
  activeChatName: string | null
  activeDmPeerSub: string | null
  userAvatarBySub: Record<string, string | undefined>
  avatarFocalBySub: Record<string, { x: number; y: number } | undefined>
  presenceBySub: Record<string, UserPresence>
  lastSeenBySub: Record<string, string | null>
  dmSoundEnabled: boolean
  headerTitle: string
  sortedChats: Chat[]
  currentUserSub: string | null
  userMap: Record<string, string>
  dmNotifTick: number
  pickerSearch: string
  setPickerSearch: (v: string) => void
  groupTitle: string
  setGroupTitle: (v: string) => void
  groupSelected: Record<string, boolean>
  setGroupSelected: Dispatch<SetStateAction<Record<string, boolean>>>
  filteredUsers: PortalUser[]
  mentionCandidatesForActiveChat: PortalUser[]
  messages: ChatMessage[]
  replyTo: ChatMessage | null
  clearReply: () => void
  replyQuoteText: string | null
  onReply: (message: ChatMessage, quoteText?: string) => void
  sendMutationPending: boolean
  openDmMutationPending: boolean
  openDmMutationError: boolean
  createGroupMutationPending: boolean
  createGroupMutationError: boolean
  canSubmitGroup: boolean
  goToList: () => void
  openChat: (chatId: string) => void
  handleDmSoundClick: (e: React.MouseEvent, chatId: string) => void
  setGroupSettingsOpen: (v: boolean) => void
  setChatCtxMenu: (v: { x: number; y: number; chat: Chat } | null) => void
  openDmMutationMutate: (sub: string) => void
  createGroupMutationMutate: () => void
  sendMutationMutateAsync: (args: {
    chatId: string
    body: string
    attachmentIds: string[]
    replyMid?: string | null
    replyQuoteText?: string | null
    replyPreview?: ChatMessage['reply_to']
    mentions?: string[]
  }) => Promise<ChatMessage>
  ephemeralPeers: EphemeralPeer[]
  notifyEphemeral: (event: 'typing' | 'voice_recording', active: boolean) => void
  onAfterForward: (targetId: string) => void
  onChatActivity?: () => void
  emojiPong?: ReturnType<typeof useEmojiPongOnline> | null
}

export function FloatingDmWidgetPanel({
  view,
  setView,
  panelHidden = false,
  onMinimize,
  onClosePanel,
  activeChatId,
  activeChat,
  activeChatName,
  activeDmPeerSub,
  userAvatarBySub,
  avatarFocalBySub,
  presenceBySub,
  lastSeenBySub,
  dmSoundEnabled,
  headerTitle,
  sortedChats,
  currentUserSub,
  userMap,
  dmNotifTick,
  pickerSearch,
  setPickerSearch,
  groupTitle,
  setGroupTitle,
  groupSelected,
  setGroupSelected,
  filteredUsers,
  mentionCandidatesForActiveChat,
  messages,
  replyTo,
  clearReply,
  replyQuoteText,
  onReply,
  sendMutationPending,
  openDmMutationPending,
  openDmMutationError,
  createGroupMutationPending,
  createGroupMutationError,
  canSubmitGroup,
  goToList,
  openChat,
  handleDmSoundClick,
  setGroupSettingsOpen,
  setChatCtxMenu,
  openDmMutationMutate,
  createGroupMutationMutate,
  sendMutationMutateAsync,
  ephemeralPeers,
  notifyEphemeral,
  onAfterForward,
  onChatActivity,
  emojiPong = null,
}: FloatingDmWidgetPanelProps) {
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

  return (
    <div className={[styles.panel, panelHidden ? styles.panelHidden : ''].filter(Boolean).join(' ')}>
      <div className={styles.header}>
        {view !== 'list' && (
          <button
            type="button"
            className={styles.backBtn}
            onClick={() => {
              if (view === 'chat') {
                clearReply()
                setGroupSettingsOpen(false)
                setView('list')
              } else {
                goToList()
              }
            }}
            aria-label="Назад"
          >
            ‹
          </button>
        )}
        {view === 'chat' && activeChat ? (
          <div className={styles.headerChatMain}>
            {activeChat.is_direct && activeDmPeerSub ? (
              <UserAvatar
                size={36}
                label={activeChatName ?? 'Чат'}
                imageUrl={resolveChatAvatarImageUrl({
                  isDirect: true,
                  peerSub: activeDmPeerSub,
                  userAvatarBySub,
                  chatAvatarUrl: activeChat.avatar_url,
                })}
                focalX={avatarFocalBySub[activeDmPeerSub]?.x}
                focalY={avatarFocalBySub[activeDmPeerSub]?.y}
                className={styles.headerDmAvatar}
                onClick={() => setGalleryOpen(true)}
                title="Вложения чата"
              />
            ) : !activeChat.is_direct ? (
              <UserAvatar
                size={36}
                label={activeChatName ?? 'Чат'}
                imageUrl={resolveChatAvatarImageUrl({
                  isDirect: false,
                  peerSub: null,
                  userAvatarBySub,
                  chatAvatarUrl: activeChat.avatar_url,
                })}
                focalX={activeChat.avatar_focal_x ?? undefined}
                focalY={activeChat.avatar_focal_y ?? undefined}
                className={styles.headerDmAvatar}
                onClick={() => setGroupSettingsOpen(true)}
                title="Настройки чата"
              />
            ) : null}
            <div className={styles.headerTitleColumn}>
              <div className={styles.headerTitleRow}>
                <button
                  type="button"
                  className={styles.headerMainTitle}
                  onClick={() => {
                    if (!activeChat.is_direct) {
                      setGroupSettingsOpen(true)
                      return
                    }
                    setGalleryOpen(true)
                  }}
                  title={
                    !activeChat.is_direct ? 'Настройки чата' : 'Вложения чата'
                  }
                >
                  {activeChatName ?? 'Чат'}
                </button>
                {activeChat.is_direct && activeDmPeerSub ? (
                  <PresenceInline
                    presence={presenceBySub[activeDmPeerSub]}
                    lastSeenAt={lastSeenBySub[activeDmPeerSub]}
                  />
                ) : null}
              </div>
            </div>
          </div>
        ) : (
          <span className={styles.headerTitle}>{headerTitle}</span>
        )}
        {view === 'chat' && activeChatId && activeChat ? (
          <div className={styles.headerChatActions}>
            <button
              type="button"
              className={styles.headerSoundBtn}
              onClick={(e) => handleDmSoundClick(e, activeChatId)}
              title={dmSoundEnabled ? 'Выключить звук' : 'Включить звук'}
              aria-pressed={dmSoundEnabled}
              aria-label={dmSoundEnabled ? 'Звук уведомлений включён' : 'Звук уведомлений выключен'}
            >
              {dmSoundEnabled ? <IconVolumeOn /> : <IconVolumeOff />}
            </button>
            <button
              type="button"
              className={styles.headerAttachmentsBtn}
              onClick={() => setGalleryOpen(true)}
              title="Вложения"
              aria-label="Вложения чата"
            >
              <IconPaperclip />
            </button>
            <ChatHeaderOverflowMenu
              chatId={activeChatId}
              onOpenInChatsNavigate={onClosePanel}
              onOpenSettings={!activeChat.is_direct ? () => setGroupSettingsOpen(true) : undefined}
            />
          </div>
        ) : null}
        <button
          type="button"
          className={styles.minimizeBtn}
          onClick={onMinimize}
          aria-label="Свернуть"
          title="Свернуть"
        >
          −
        </button>
        <button
          type="button"
          className={styles.closeBtn}
          onClick={onClosePanel}
          aria-label="Закрыть"
        >
          ×
        </button>
      </div>

      {view === 'list' && (
        <ChatListPanel
          sortedChats={sortedChats}
          currentUserSub={currentUserSub}
          userMap={userMap}
          userAvatarBySub={userAvatarBySub}
          presenceBySub={presenceBySub}
          lastSeenBySub={lastSeenBySub}
          avatarFocalBySub={avatarFocalBySub}
          dmNotifTick={dmNotifTick}
          onChatOpen={openChat}
          onDmSoundClick={handleDmSoundClick}
          onNewDm={() => {
            setPickerSearch('')
            setView('picker')
          }}
          onNewGroup={() => {
            setPickerSearch('')
            setGroupTitle('')
            setGroupSelected({})
            setView('groupPicker')
          }}
          onOpenFullscreen={onClosePanel}
          onChatRowContextMenu={(e, chat) =>
            setChatCtxMenu({ x: e.clientX, y: e.clientY, chat })
          }
        />
      )}

      {view === 'picker' && (
        <DmPickerPanel
          pickerSearch={pickerSearch}
          filteredUsers={filteredUsers}
          userMap={userMap}
          isPending={openDmMutationPending}
          isError={openDmMutationError}
          onPickerSearchChange={setPickerSearch}
          onSelectUser={(sub) => openDmMutationMutate(sub)}
        />
      )}

      {view === 'groupPicker' && (
        <CreateGroupPanel
          groupTitle={groupTitle}
          pickerSearch={pickerSearch}
          groupSelected={groupSelected}
          filteredUsers={filteredUsers}
          userMap={userMap}
          error={createGroupMutationError ? 'Не удалось создать группу.' : null}
          isPending={createGroupMutationPending}
          canSubmit={canSubmitGroup}
          onGroupTitleChange={setGroupTitle}
          onPickerSearchChange={setPickerSearch}
          onMemberToggle={(sub, checked) =>
            setGroupSelected((prev) => ({ ...prev, [sub]: checked }))
          }
          onSubmit={() => createGroupMutationMutate()}
        />
      )}

      {view === 'chat' && activeChatId && (
        <ActiveChatPanel
          activeChatId={activeChatId}
          messages={messages}
          currentUserSub={currentUserSub}
          userMap={userMap}
          userAvatarBySub={userAvatarBySub}
          ephemeralPeers={ephemeralPeers}
          replyTo={replyTo}
          replyQuoteText={replyQuoteText}
          sortedChats={sortedChats}
          mentionUsers={mentionCandidatesForActiveChat}
          sendPending={sendMutationPending}
          onReply={onReply}
          onClearReply={clearReply}
          onEphemeralActivity={notifyEphemeral}
          onSend={async (body, attachmentIds, replyMid, mentions, quote) => {
            await sendMutationMutateAsync({
              chatId: activeChatId,
              body,
              attachmentIds,
              replyMid,
              replyQuoteText: quote,
              replyPreview: buildOptimisticReplyPreview(replyTo, replyMid, quote),
              mentions,
            })
          }}
          onAfterForward={onAfterForward}
          onChatActivity={onChatActivity}
          jumpMessageId={jumpMessageId}
          onJumpToMessage={setJumpMessageId}
          isDirect={Boolean(activeChat?.is_direct)}
          peerUserSub={activeDmPeerSub}
          emojiPong={emojiPong}
        />
      )}

      {activeChatId ? (
        <ChatAttachmentsGalleryModal
          open={galleryOpen}
          chatId={activeChatId}
          onClose={() => setGalleryOpen(false)}
          onJumpToMessage={setJumpMessageId}
        />
      ) : null}
    </div>
  )
}
