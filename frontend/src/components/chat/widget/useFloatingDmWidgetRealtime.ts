import { useCallback, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import type { Chat, ChatMessage } from '../../../types/chat'
import { useChatActivityRead } from '../../../hooks/useChatActivityRead'
import { useChatEphemeral } from '../../../hooks/useChatEphemeral'
import { useChatWebSocket } from '../../../hooks/useChatWebSocket'
import { useEmojiPongOnline } from '../../../hooks/useEmojiPongOnline'
import { markChatRead } from '../../../api/chat/chatApi'
import { portalPinnedMessagesQueryKey } from '../../../api/queryKeys'
import { applyChatEventToList, patchOwnReceiptFromWs } from '@/utils/chat/chatWs'
import { invalidatePortalSearchQueries } from '@/utils/search/invalidatePortalSearch'
import { patchPortalChatUnreadZero } from '../../../utils/chat/patchPortalChatsUnread'

type Args = {
  chatIdForWs: string | null
  chatIdForEphemeral: string | null
  currentUserSub: string | null
  activeChatId: string | null
  view: string
  panelMounted: boolean
  minimized: boolean
  activeChat: Chat | undefined
  invalidateChatQueries: () => void
  clearReply: () => void
  setGroupSettingsOpen: (open: boolean) => void
  setActiveChatId: (id: string | null) => void
  setView: (view: 'list' | 'picker' | 'groupPicker' | 'chat') => void
}

/**
 * Realtime-слой плавающего DM-виджета: WebSocket-подписка, эфемерные события
 * (печатает/запись голоса), онлайн emoji-pong, отметка прочтения активности и
 * маршрутизация WS-событий чата (read_state, members/meta, chat_deleted,
 * message_*). Мутации и сессионное состояние — в компоненте и
 * {@link useFloatingDmWidgetMutations}.
 */
export function useFloatingDmWidgetRealtime({
  chatIdForWs,
  chatIdForEphemeral,
  currentUserSub,
  activeChatId,
  view,
  panelMounted,
  minimized,
  activeChat,
  invalidateChatQueries,
  clearReply,
  setGroupSettingsOpen,
  setActiveChatId,
  setView,
}: Args) {
  const qc = useQueryClient()

  const { ephemeralPeers, notifyEphemeral, handleWsEvent, bindSendEphemeral } = useChatEphemeral(
    chatIdForEphemeral,
    currentUserSub,
  )

  const emojiPong = useEmojiPongOnline({
    chatId: chatIdForEphemeral,
    currentUserSub,
    isDirect: Boolean(activeChat?.is_direct),
  })
  const onChatActivity = useChatActivityRead(
    view === 'chat' && panelMounted && !minimized ? activeChatId : null,
    activeChat?.unread_count ?? 0,
  )

  const markReadOnMessageRef = useRef<number>(0)
  const markReadOnIncomingMessage = useCallback(
    (chatId: string) => {
      const now = Date.now()
      if (now - markReadOnMessageRef.current < 1500) return
      markReadOnMessageRef.current = now
      void markChatRead(chatId).then(() => patchPortalChatUnreadZero(qc, chatId))
    },
    [qc],
  )

  useChatWebSocket(chatIdForWs, {
    onConnection: (send) => {
      bindSendEphemeral(send)
      emojiPong.bindSend(send)
    },
    onEvent: (e) => {
      if (e.type === 'ignored') return
      if (handleWsEvent(e)) return
      if (emojiPong.handleWsEvent(e)) return

      if (e.type === 'read_state_updated') {
        if (activeChatId && currentUserSub) {
          qc.setQueryData<ChatMessage[]>(['portal', 'messages', activeChatId], (prev) =>
            prev?.map((m) =>
              m.author_sub === currentUserSub && m.receipt !== 'read'
                ? { ...m, receipt: 'read' as const }
                : m,
            ) ?? [],
          )
        }
        return
      }
      if (e.type === 'members_updated' || e.type === 'chat_meta_updated') {
        invalidateChatQueries()
        return
      }
      if (e.type === 'chat_deleted') {
        invalidateChatQueries()
        invalidatePortalSearchQueries(qc)
        if (activeChatId === e.chat_id) {
          setActiveChatId(null)
          clearReply()
          setGroupSettingsOpen(false)
          setView('list')
        }
        return
      }
      if (e.type === 'message_created' || e.type === 'message_updated' || e.type === 'message_deleted') {
        invalidatePortalSearchQueries(qc)
      }
      if (e.type === 'message_updated') {
        void qc.invalidateQueries({ queryKey: portalPinnedMessagesQueryKey(e.message.chat_id) })
      }
      if (
        e.type === 'message_created' &&
        view === 'chat' &&
        activeChatId &&
        e.message.author_sub !== currentUserSub
      ) {
        markReadOnIncomingMessage(activeChatId)
      }
      const messageChatId =
        e.type === 'message_created' ||
        e.type === 'message_updated' ||
        e.type === 'message_deleted'
          ? e.message.chat_id
          : null
      if (!messageChatId) return
      qc.setQueryData<ChatMessage[]>(['portal', 'messages', messageChatId], (prev) => {
        const next = applyChatEventToList(prev, e)
        return patchOwnReceiptFromWs(next, e, currentUserSub)
      })
    },
  })

  return { emojiPong, ephemeralPeers, notifyEphemeral, onChatActivity }
}
