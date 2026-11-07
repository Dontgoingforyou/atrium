import { useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import type { ChatMessage } from '../../types/chat'
import { portalPinnedMessagesQueryKey } from '../../api/queryKeys'
import { useChatEphemeral } from '../../hooks/useChatEphemeral'
import { useEmojiPongOnline } from '../../hooks/useEmojiPongOnline'
import { useChatWebSocket, type ChatWsSendJson } from '../../hooks/useChatWebSocket'
import { applyChatEventToList, patchOwnReceiptFromWs } from '@/utils/chat/chatWs'
import { invalidatePortalSearchQueries } from '@/utils/search/invalidatePortalSearch'
import { MESSAGE_DELETE_EXIT_MS } from './chatsConstants'
import type { BuildPortalMessagesPageQueryKey } from './chatsQueryKeys'

type Args = {
  activeChatId: string | null
  buildPortalMessagesQueryKey: BuildPortalMessagesPageQueryKey
  currentUserSub: string | null
  isDirect: boolean
  invalidateChatQueries: () => void
  onChatDeletedReset: () => void
  /** Колбэк: сообщение начало анимацию исчезновения по WS-событию (до удаления из кэша). */
  onWsMessageDeleting?: (messageId: string) => void
}

export function useChatsPageMessagesWebSocket({
  activeChatId,
  buildPortalMessagesQueryKey,
  currentUserSub,
  isDirect,
  invalidateChatQueries,
  onChatDeletedReset,
  onWsMessageDeleting,
}: Args) {
  const qc = useQueryClient()
  const readStateDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const { ephemeralHint, ephemeralPeers, notifyEphemeral, handleWsEvent, bindSendEphemeral } =
    useChatEphemeral(activeChatId, currentUserSub)
  const emojiPong = useEmojiPongOnline({
    chatId: activeChatId,
    currentUserSub,
    isDirect,
  })

  useChatWebSocket(activeChatId, {
    onConnection: (send: ChatWsSendJson) => {
      bindSendEphemeral(send)
      emojiPong.bindSend(send)
    },
    onEvent: (e) => {
      if (e.type === 'ignored') return
      if (handleWsEvent(e)) return
      if (emojiPong.handleWsEvent(e)) return

      if (e.type === 'read_state_updated') {
        if (activeChatId && currentUserSub) {
          if (readStateDebounceRef.current) clearTimeout(readStateDebounceRef.current)
          readStateDebounceRef.current = setTimeout(() => {
            qc.setQueryData<ChatMessage[]>(buildPortalMessagesQueryKey(activeChatId), (prev) =>
              prev?.map((m) =>
                m.author_sub === currentUserSub && m.receipt !== 'read'
                  ? { ...m, receipt: 'read' as const }
                  : m,
              ) ?? [],
            )
          }, 400)
        }
        return
      }
      if (e.type === 'members_updated' || e.type === 'chat_meta_updated') {
        invalidateChatQueries()
        return
      }
      if (e.type === 'chat_deleted') {
        invalidateChatQueries()
        if (activeChatId === e.chat_id) {
          onChatDeletedReset()
        }
        return
      }
      if (!activeChatId) return

      if (e.type === 'message_created' || e.type === 'message_updated') {
        invalidatePortalSearchQueries(qc)
      }
      if (e.type === 'message_updated') {
        void qc.invalidateQueries({ queryKey: portalPinnedMessagesQueryKey(activeChatId) })
      }

      if (e.type === 'message_deleted' && e.message?.id) {
        if (e.message.chat_id !== activeChatId) return
        const deletedId = e.message.id
        invalidatePortalSearchQueries(qc)
        onWsMessageDeleting?.(deletedId)
        window.setTimeout(() => {
          qc.setQueryData<ChatMessage[]>(buildPortalMessagesQueryKey(activeChatId), (prev) =>
            prev?.filter((x) => x.id !== deletedId) ?? [],
          )
        }, MESSAGE_DELETE_EXIT_MS)
        return
      }

      if ('message' in e && e.message.chat_id !== activeChatId) return

      qc.setQueryData<ChatMessage[]>(buildPortalMessagesQueryKey(activeChatId), (prev) => {
        const next = applyChatEventToList(prev, e)
        return patchOwnReceiptFromWs(next, e, currentUserSub)
      })
    },
  })

  return { ephemeralHint, ephemeralPeers, notifyEphemeral, emojiPong }
}
