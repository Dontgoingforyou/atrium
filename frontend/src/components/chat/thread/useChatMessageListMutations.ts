import { useMutation, useQueryClient } from '@tanstack/react-query'

import {
  deleteMessage,
  forwardMessage,
  patchMessage,
  pinMessage,
  toggleMessageReaction,
  transcribeAttachment,
  unpinMessage,
} from '../../../api/chat/chatApi'
import { PORTAL_CHATS_ALL_QUERY_KEY, portalPinnedMessagesQueryKey } from '../../../api/queryKeys'
import type { ChatMessage } from '../../../types/chat'
import { userFacingMessageFromUnknown } from '../../../utils/apiUserMessage'
import { invalidatePortalSearchQueries } from '@/utils/search/invalidatePortalSearch'
import { recordReactionEmojiUse } from '@/utils/chat/chatReactionFrequent'
import { MESSAGE_DELETE_EXIT_MS } from '../../../pages/chats/chatsConstants'

type Args = {
  chatId: string
  /** Ключ кэша сообщений (на странице /chats — с суффиксом wide|default). */
  messagesQueryKey?: readonly unknown[]
  /** Анимация схлопывания строки перед удалением из кэша. */
  onDeleteForAllExitAnimate?: {
    onStart: (messageId: string) => void
    onEnd: (messageId: string) => void
  }
  closeMenu: () => void
  setEditing: (v: { id: string; body: string } | null) => void
  setActionError: (v: string | null) => void
  onAfterForward?: (targetChatId: string) => void
  /** Сброс модалки пересылки после успешной мутации */
  onForwardMutSuccess?: () => void
}

// Импортируется из chatsConstants для консистентности с WS-удалением
const DELETE_FOR_ALL_EXIT_MS = MESSAGE_DELETE_EXIT_MS

export function useChatMessageListMutations({
  chatId,
  messagesQueryKey,
  onDeleteForAllExitAnimate,
  closeMenu,
  setEditing,
  setActionError,
  onAfterForward,
  onForwardMutSuccess,
}: Args) {
  const qc = useQueryClient()
  const cacheKey = messagesQueryKey ?? (['portal', 'messages', chatId] as const)

  const patchMut = useMutation({
    mutationFn: async ({ id, body }: { id: string; body: string }) =>
      patchMessage(chatId, id, { body }),
    onSuccess: (m) => {
      qc.setQueryData<ChatMessage[]>(cacheKey, (prev) =>
        prev?.map((x) => (x.id === m.id ? m : x)) ?? [m],
      )
      invalidatePortalSearchQueries(qc)
      setEditing(null)
      setActionError(null)
    },
    onError: (e) => {
      setActionError(userFacingMessageFromUnknown(e))
    },
  })

  const deleteMeMut = useMutation({
    mutationFn: (id: string) => deleteMessage(chatId, id, 'me'),
    onSuccess: (_, id) => {
      qc.setQueryData<ChatMessage[]>(cacheKey, (prev) =>
        prev?.filter((m) => m.id !== id) ?? [],
      )
      invalidatePortalSearchQueries(qc)
      closeMenu()
      setActionError(null)
    },
    onError: (e) => {
      setActionError(userFacingMessageFromUnknown(e))
    },
  })

  const pinMut = useMutation({
    mutationFn: ({ messageId, pinned }: { messageId: string; pinned: boolean }) =>
      pinned ? unpinMessage(chatId, messageId) : pinMessage(chatId, messageId),
    onSuccess: (updated) => {
      qc.setQueryData<ChatMessage[]>(cacheKey, (prev) =>
        prev?.map((x) => (x.id === updated.id ? updated : x)) ?? [updated],
      )
      void qc.invalidateQueries({ queryKey: portalPinnedMessagesQueryKey(chatId) })
    },
    onError: (e) => {
      setActionError(userFacingMessageFromUnknown(e))
    },
  })

  const reactionMut = useMutation({
    mutationFn: ({ messageId, emoji }: { messageId: string; emoji: string }) =>
      toggleMessageReaction(chatId, messageId, emoji),
    onSuccess: (updated, { messageId, emoji }) => {
      recordReactionEmojiUse(emoji)
      qc.setQueryData<ChatMessage[]>(cacheKey, (prev) =>
        prev?.map((x) => (x.id === updated.id ? updated : x)) ?? [updated],
      )
      void qc.invalidateQueries({
        queryKey: ['portal', 'message-reactors', chatId, messageId],
      })
    },
    onError: (e) => {
      setActionError(userFacingMessageFromUnknown(e))
    },
  })

  const transcribeMut = useMutation({
    mutationFn: ({ attachmentId }: { messageId: string; attachmentId: string }) =>
      transcribeAttachment(chatId, attachmentId),
    onSuccess: (updatedAttachment, { messageId }) => {
      qc.setQueryData<ChatMessage[]>(cacheKey, (prev) =>
        prev?.map((m) =>
          m.id !== messageId
            ? m
            : {
                ...m,
                attachments: m.attachments?.map((a) =>
                  a.id === updatedAttachment.id ? updatedAttachment : a,
                ),
              },
        ) ?? prev,
      )
    },
    onError: (e) => {
      setActionError(userFacingMessageFromUnknown(e))
    },
  })

  const forwardMut = useMutation({
    mutationFn: ({
      targetChatId,
      fromChatId,
      messageId,
    }: {
      targetChatId: string
      fromChatId: string
      messageId: string
    }) => forwardMessage(targetChatId, fromChatId, messageId),
    onSuccess: (newMsg, vars) => {
      qc.setQueriesData<ChatMessage[]>(
        { queryKey: ['portal', 'messages', vars.targetChatId] },
        (prev) => {
          if (!prev) return [newMsg]
          if (prev.some((m) => m.id === newMsg.id)) return prev
          return [...prev, newMsg]
        },
      )
      void qc.invalidateQueries({ queryKey: PORTAL_CHATS_ALL_QUERY_KEY })
      invalidatePortalSearchQueries(qc)
      onAfterForward?.(vars.targetChatId)
      onForwardMutSuccess?.()
      closeMenu()
      setActionError(null)
    },
    onError: (e) => {
      setActionError(userFacingMessageFromUnknown(e))
    },
  })

  const deleteAllMut = useMutation({
    mutationFn: (id: string) => deleteMessage(chatId, id, 'all'),
    onMutate: (id) => {
      closeMenu()
      onDeleteForAllExitAnimate?.onStart(id)
    },
    onSuccess: (_, id) => {
      invalidatePortalSearchQueries(qc)
      window.setTimeout(() => {
        qc.setQueryData<ChatMessage[]>(cacheKey, (prev) =>
          prev?.filter((m) => m.id !== id) ?? [],
        )
        onDeleteForAllExitAnimate?.onEnd(id)
        setActionError(null)
      }, DELETE_FOR_ALL_EXIT_MS)
    },
    onError: (e, id) => {
      setActionError(userFacingMessageFromUnknown(e))
      if (id) onDeleteForAllExitAnimate?.onEnd(id)
    },
  })

  const busy =
    patchMut.isPending
    || deleteMeMut.isPending
    || deleteAllMut.isPending
    || reactionMut.isPending
    || forwardMut.isPending
    || pinMut.isPending

  return {
    patchMut,
    deleteMeMut,
    deleteAllMut,
    reactionMut,
    forwardMut,
    pinMut,
    transcribeMut,
    busy,
  }
}
