import {
  memo,
  useRef,
  useState,
  useEffect,
  useCallback,
} from 'react'
import { createPortal } from 'react-dom'
import { useVirtualizer } from '@tanstack/react-virtual'

import { useThemeStore } from '../../../store/themeStore'
import type { ChatMessage } from '../../../types/chat'
import { useSearchHighlightQuery } from '../../../hooks/useSearchHighlightQuery'
import { ForwardToChatModal } from './ForwardToChatModal'
import { MessageContextMenu, type MenuState } from './MessageContextMenu'
import { ChatMessageListRow } from './ChatMessageListRow'
import { ChatMessageReadersPopover } from './ChatMessageReadersPopover'
import { ChatMessageReactorsPopover } from './ChatMessageReactorsPopover'
import { useChatMessageListMutations } from './useChatMessageListMutations'
import { useChatMessageListAutoscroll } from './useChatMessageListAutoscroll'
import { EmojiCatchGameModal } from '../emojiGame/EmojiCatchGameModal'
import { EmojiPongInviteBanner } from '../emojiGame/EmojiPongInviteBanner'
import {
  findTourDemoEmojiIndex,
  findTourDemoTextIndex,
} from '../../../onboarding/ensureTourDemoChat'
import {
  REPLY_JUMP_HIGHLIGHT_MS,
  REPLY_JUMP_PENDING_TIMEOUT_MS,
} from '@/utils/chat/messageQuoteSelection'
import layout from '@/styles/modules/chat/ChatMessageListLayout.module.css'
import type {
  ChatMessageListProps,
  CtxEmojiPicker,
  ReadersPopover,
  ReactorsPopover,
} from './chatMessageListTypes'
import { useChatMessageListEmojiGame } from './useChatMessageListEmojiGame'
import { useChatMessageListGuidedTour } from './useChatMessageListGuidedTour'

export const ChatMessageList = memo(function ChatMessageList({
  chatId,
  messagesQueryKey,
  messages,
  currentUserSub,
  userMap = {},
  userAvatarBySub = {},
  threadLayout = false,
  onReply,
  chatsForForward = [],
  onAfterForward,
  scrollToMessageId = null,
  onDeepLinkScrollConsumed,
  wsDeleteExitRowId = null,
  highlightedMessageId = null,
  isDirect = false,
  peerUserSub = null,
  emojiPong = null,
}: ChatMessageListProps) {
  const theme = useThemeStore((s) => s.theme)
  const highlightQuery = useSearchHighlightQuery()
  const containerRef = useRef<HTMLDivElement>(null)
  const onDeepLinkScrollConsumedRef = useRef(onDeepLinkScrollConsumed)
  onDeepLinkScrollConsumedRef.current = onDeepLinkScrollConsumed
  const messagesRef = useRef(messages)
  messagesRef.current = messages
  const [menu, setMenu] = useState<MenuState | null>(null)
  const [editing, setEditing] = useState<{ id: string; body: string } | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [forwardSource, setForwardSource] = useState<ChatMessage | null>(null)
  const [ctxEmojiPicker, setCtxEmojiPicker] = useState<CtxEmojiPicker | null>(null)
  const [readersPopover, setReadersPopover] = useState<ReadersPopover | null>(null)
  const [reactorsPopover, setReactorsPopover] = useState<ReactorsPopover | null>(null)
  const [deleteExitRowId, setDeleteExitRowId] = useState<string | null>(null)
  const [localJumpId, setLocalJumpId] = useState<string | null>(null)
  /** Подсветка исходного фрагмента после клика по цитате в ответе. */
  const [replyJumpHighlight, setReplyJumpHighlight] = useState<{
    messageId: string
    quote: string
  } | null>(null)

  const handleJumpToReply = useCallback((messageId: string, quoteText?: string | null) => {
    setLocalJumpId(messageId)
    const quote = quoteText?.trim()
    setReplyJumpHighlight(quote ? { messageId, quote } : null)
  }, [])

  useEffect(() => {
    if (!replyJumpHighlight) return
    const timer = window.setTimeout(() => setReplyJumpHighlight(null), REPLY_JUMP_HIGHLIGHT_MS)
    return () => window.clearTimeout(timer)
  }, [replyJumpHighlight])

  useEffect(() => {
    setLocalJumpId(null)
    setReplyJumpHighlight(null)
  }, [chatId])

  // Если целевого сообщения нет в загруженной ленте — не держать jump вечно
  // (иначе early-return в autoscroll блокирует stick-to-bottom).
  useEffect(() => {
    if (!localJumpId) return
    const timer = window.setTimeout(() => setLocalJumpId(null), REPLY_JUMP_PENDING_TIMEOUT_MS)
    return () => window.clearTimeout(timer)
  }, [localJumpId])

  const {
    emojiGame,
    shareError: emojiGameShareError,
    sharePending: emojiGameSharePending,
    openEmojiGame,
    closeEmojiGame,
    shareScore,
    peerPlayer,
    mePlayer,
  } = useChatMessageListEmojiGame({
    chatId,
    isDirect,
    currentUserSub,
    messages,
    messagesQueryKey,
    peerUserSub,
    userMap,
    userAvatarBySub,
    emojiPong,
  })

  const closeMenu = useCallback(() => {
    setMenu(null)
    setCtxEmojiPicker(null)
  }, [])

  const { patchMut, deleteMeMut, deleteAllMut, reactionMut, forwardMut, pinMut, transcribeMut, busy } =
    useChatMessageListMutations({
      chatId,
      messagesQueryKey,
      onDeleteForAllExitAnimate: {
        onStart: (id) => setDeleteExitRowId(id),
        onEnd: () => setDeleteExitRowId(null),
      },
      closeMenu,
      setEditing,
      setActionError,
      onAfterForward,
      onForwardMutSuccess: () => setForwardSource(null),
    })

  // TanStack Virtual возвращает функции, которые нельзя мемоизировать без stale UI.
  // eslint-disable-next-line react-hooks/incompatible-library -- useVirtualizer API
  const virtualizer = useVirtualizer({
    count: messages.length,
    getScrollElement: () => containerRef.current,
    estimateSize: () => 80,
    overscan: 5,
  })
  const virtualizerRef = useRef(virtualizer)
  virtualizerRef.current = virtualizer

  useChatMessageListGuidedTour({
    messagesRef,
    virtualizerRef,
    containerRef,
    setMenu,
    setActionError,
  })

  const isEmpty = messages.length === 0
  const effectiveScrollToMessageId = localJumpId ?? scrollToMessageId

  useChatMessageListAutoscroll({
    chatId,
    messages,
    messagesRef,
    containerRef,
    virtualizer,
    isEmpty,
    currentUserSub,
    editingId: editing?.id,
    effectiveScrollToMessageId,
    localJumpId,
    setLocalJumpId,
    onDeepLinkScrollConsumedRef,
  })

  useEffect(() => {
    if (!menu) return
    const onDoc = (e: Event) => {
      // Во время тура меню открыто намеренно (демо ПКМ) — не закрывать от scroll/layout.
      if (
        e.type === 'scroll' &&
        document.documentElement.getAttribute('data-guided-tour') === '1'
      ) {
        return
      }
      const t = e.target
      if (
        t instanceof HTMLElement &&
        (t.closest?.('[data-ctx-emoji-popover]') || t.closest?.('[data-ctx-message-menu]'))
      ) {
        return
      }
      closeMenu()
    }
    document.addEventListener('click', onDoc)
    document.addEventListener('scroll', onDoc, true)
    return () => {
      document.removeEventListener('click', onDoc)
      document.removeEventListener('scroll', onDoc, true)
    }
  }, [menu, closeMenu])

  useEffect(() => {
    if (!ctxEmojiPicker) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setCtxEmojiPicker(null)
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [ctxEmojiPicker])

  const containerClass = `${layout.container}${threadLayout ? ` ${layout.containerThread}` : ''}`

  if (isEmpty) {
    return (
      <div ref={containerRef} className={containerClass} data-tour="chats-messages">
        <p className={layout.empty}>Нет сообщений</p>
      </div>
    )
  }

  const virtualItems = virtualizer.getVirtualItems()
  const tourMessageRowIndex = findTourDemoTextIndex(messages)
  const tourEmojiIndex = findTourDemoEmojiIndex(messages)

  return (
    <div ref={containerRef} className={containerClass} data-tour="chats-messages">
      {emojiPong?.incomingInvite ? (
        <EmojiPongInviteBanner
          invite={emojiPong.incomingInvite}
          onAccept={emojiPong.acceptInvite}
          onDecline={emojiPong.declineInvite}
        />
      ) : null}
      {actionError && <p className={layout.actionError}>{actionError}</p>}
      <div
        className={layout.virtualInner}
        style={{ height: `${virtualizer.getTotalSize()}px` }}
      >
        {virtualItems.map((virtualRow) => {
          const msg = messages[virtualRow.index]
          return (
            <ChatMessageListRow
              key={msg.id}
              virtualRow={virtualRow}
              measureElement={virtualizer.measureElement}
              msg={msg}
              messages={messages}
              rowLeaving={deleteExitRowId === msg.id || wsDeleteExitRowId === msg.id}
              // localJumpId без обводки: пульс 3px визуально раздувал пузырь при клике по цитате
              highlighted={highlightedMessageId === msg.id}
              highlightQuery={
                replyJumpHighlight?.messageId === msg.id
                  ? replyJumpHighlight.quote
                  : highlightQuery
              }
              highlightExact={replyJumpHighlight?.messageId === msg.id}
              currentUserSub={currentUserSub}
              userMap={userMap}
              userAvatarBySub={userAvatarBySub}
              editing={editing}
              setEditing={setEditing}
              busy={busy}
              patchMut={patchMut}
              transcribeMut={transcribeMut}
              setMenu={setMenu}
              setActionError={setActionError}
              setReadersPopover={setReadersPopover}
              onOpenReactors={(messageId, emoji, rect) =>
                setReactorsPopover({
                  messageId,
                  emoji,
                  anchorRect: {
                    top: rect.top,
                    bottom: rect.bottom,
                    left: rect.left,
                    right: rect.right,
                  },
                })
              }
              onJumpToReply={handleJumpToReply}
              onEmojiGameOpen={openEmojiGame}
              isTourAnchor={virtualRow.index === tourMessageRowIndex}
              isTourEmojiAnchor={virtualRow.index === tourEmojiIndex}
            />
          )
        })}
      </div>

      {menu && createPortal(
        <MessageContextMenu
          menu={menu}
          chatId={chatId}
          currentUserSub={currentUserSub}
          chatsForForward={chatsForForward}
          busy={busy}
          theme={theme}
          ctxEmojiPicker={ctxEmojiPicker}
          userMap={userMap}
          userAvatarBySub={userAvatarBySub}
          onClose={closeMenu}
          onReply={onReply}
          onEdit={(id, body) => setEditing({ id, body })}
          onDeleteMe={(id) => deleteMeMut.mutate(id)}
          onDeleteAll={(id) => deleteAllMut.mutate(id)}
          onForward={(m) => setForwardSource(m)}
          onReactionToggle={async (messageId, emoji) => {
            await reactionMut.mutateAsync({ messageId, emoji })
          }}
          onEmojiPickerToggle={setCtxEmojiPicker}
          onPinToggle={(m) => pinMut.mutate({ messageId: m.id, pinned: Boolean(m.pinned_at) })}
        />,
        document.body,
      )}

      <ForwardToChatModal
        key={forwardSource ? `fwd-${forwardSource.id}` : 'fwd-closed'}
        open={forwardSource != null}
        onClose={() => setForwardSource(null)}
        chats={chatsForForward}
        currentUserSub={currentUserSub}
        userMap={userMap}
        busy={forwardMut.isPending}
        onSelect={(targetChatId) => {
          if (!forwardSource) return
          forwardMut.mutate({
            targetChatId,
            fromChatId: chatId,
            messageId: forwardSource.id,
          })
        }}
      />

      {emojiGame ? (
        <EmojiCatchGameModal
          key={emojiGame.sessionId}
          emojis={emojiGame.emojis}
          peer={peerPlayer}
          me={mePlayer}
          shareEnabled={isDirect}
          sharePending={emojiGameSharePending}
          shareError={emojiGameShareError}
          onShareScore={shareScore}
          onClose={() => {
            emojiPong?.cancelOnline()
            closeEmojiGame()
          }}
          canPlayOnline={isDirect}
          liveSession={emojiPong?.liveSession ?? null}
          waitingForAccept={emojiPong?.waitingForAccept ?? false}
          incomingInvite={emojiPong?.incomingInvite ?? null}
          netRef={emojiPong?.netRef ?? null}
          matchTick={emojiPong?.matchTick ?? 0}
          onInviteOnline={emojiPong?.invitePeer}
          onAcceptInvite={emojiPong?.acceptInvite}
          onDeclineInvite={emojiPong?.declineInvite}
          onSendPaddle={emojiPong?.sendPaddle}
          onSendState={emojiPong?.sendState}
          onSendEnd={emojiPong?.sendEnd}
          onClearOnlineSession={emojiPong?.cancelOnline}
        />
      ) : null}

      {readersPopover && (
        <ChatMessageReadersPopover
          chatId={chatId}
          messageId={readersPopover.messageId}
          anchorRect={readersPopover.anchorRect}
          userMap={userMap}
          onClose={() => setReadersPopover(null)}
        />
      )}

      {reactorsPopover && (
        <ChatMessageReactorsPopover
          chatId={chatId}
          messageId={reactorsPopover.messageId}
          emoji={reactorsPopover.emoji}
          anchorRect={reactorsPopover.anchorRect}
          userMap={userMap}
          currentUserSub={currentUserSub}
          busy={busy}
          onClose={() => setReactorsPopover(null)}
          onToggleReaction={async (messageId, emoji) => {
            await reactionMut.mutateAsync({ messageId, emoji })
          }}
        />
      )}
    </div>
  )
})
