import { useCallback } from 'react'
import { useMutation, useQueryClient, type QueryClient, type QueryKey } from '@tanstack/react-query'

import { deleteChatEntirely, postMessage } from '../api/chat/chatApi'
import {
  PORTAL_CHATS_ALL_QUERY_KEY,
  portalChatMessagesQueryKey,
} from '../api/queryKeys'
import type { ChatMessage } from '../types/chat'
import { userFacingMessageFromUnknown } from '../utils/apiUserMessage'
import { invalidatePortalSearchQueries } from '@/utils/search/invalidatePortalSearch'

/**
 * Стабильный callback для инвалидации чат-запросов:
 * список всех чатов + сообщения активного чата.
 */
export function useInvalidateChatQueries(
  qc: QueryClient,
  activeChatId: string | null,
): () => void {
  return useCallback(() => {
    void qc.invalidateQueries({ queryKey: PORTAL_CHATS_ALL_QUERY_KEY })
    if (activeChatId) {
      void qc.invalidateQueries({ queryKey: portalChatMessagesQueryKey(activeChatId) })
    }
  }, [qc, activeChatId])
}

/**
 * Мутация удаления чата.
 * Инвалидирует кэш чатов, сообщений и поиска; затем вызывает onAfterDelete
 * с caller-специфичными сайд-эффектами (сброс выбранного чата, закрытие панелей и т.п.).
 * onError — пользовательское сообщение через переданный `onErrorToast`.
 */
export function useDeleteChatMutation(
  qc: QueryClient,
  onAfterDelete: (chatId: string) => void,
  onErrorToast?: (message: string) => void,
) {
  return useMutation({
    mutationFn: (chatId: string) => deleteChatEntirely(chatId),
    onSuccess: (_, chatId) => {
      void qc.invalidateQueries({ queryKey: PORTAL_CHATS_ALL_QUERY_KEY })
      void qc.invalidateQueries({ queryKey: portalChatMessagesQueryKey(chatId) })
      invalidatePortalSearchQueries(qc)
      onAfterDelete(chatId)
    },
    onError: (e: unknown) => onErrorToast?.(userFacingMessageFromUnknown(e)),
  })
}

type SendChatMessageVars = {
  chatId: string
  body: string
  attachmentIds: string[]
  replyMid?: string | null
  replyQuoteText?: string | null
  mentions?: string[]
  replyPreview?: ChatMessage['reply_to']
}

type SendChatMessageOptions = {
  currentUserSub: string | null | undefined
  /** Фабрика ключа кэша сообщений — у /chats может включать deep-link суффикс. */
  messagesQueryKey: (chatId: string) => QueryKey
  /** Сообщение пользователю при сбое отправки, без тихого отката. */
  onErrorToast?: (message: string) => void
}

/**
 * Optimistic-отправка сообщения: общая для /chats и Floating DM.
 */
export function useSendChatMessageMutation({
  currentUserSub,
  messagesQueryKey,
  onErrorToast,
}: SendChatMessageOptions) {
  const qc = useQueryClient()

  return useMutation({
    mutationFn: ({
      chatId,
      body,
      attachmentIds,
      replyMid,
      replyQuoteText,
      mentions,
    }: SendChatMessageVars) =>
      postMessage(chatId, {
        body,
        attachment_ids: attachmentIds,
        reply_to_message_id: replyMid ?? undefined,
        reply_quote_text: replyQuoteText ?? undefined,
        mentions: mentions?.length ? mentions : undefined,
      }),
    onMutate: async (variables) => {
      if (!currentUserSub) return { tempId: null as string | null }
      const tempId = `optimistic-${crypto.randomUUID()}`
      const tempMsg: ChatMessage = {
        id: tempId,
        chat_id: variables.chatId,
        author_sub: currentUserSub,
        body: variables.body,
        created_at: new Date().toISOString(),
        updated_at: null,
        deleted_for_all_at: null,
        receipt: 'sent',
        reply_to_message_id: variables.replyMid ?? null,
        reply_quote_text: variables.replyQuoteText ?? null,
        reply_to: variables.replyPreview ?? null,
        mentions: variables.mentions,
      }
      const key = messagesQueryKey(variables.chatId)
      await qc.cancelQueries({ queryKey: key })
      qc.setQueryData<ChatMessage[]>(key, (prev) => (prev ? [...prev, tempMsg] : [tempMsg]))
      return { tempId }
    },
    onSuccess: (newMsg, variables, context) => {
      qc.setQueryData<ChatMessage[]>(messagesQueryKey(variables.chatId), (prev) => {
        if (!prev) return [newMsg]
        const withoutTemp = context?.tempId ? prev.filter((m) => m.id !== context.tempId) : prev
        if (withoutTemp.some((m) => m.id === newMsg.id)) {
          return withoutTemp.map((m) => (m.id === newMsg.id ? newMsg : m))
        }
        return [...withoutTemp, newMsg]
      })
      invalidatePortalSearchQueries(qc)
    },
    onError: (_err, variables, context) => {
      if (!context?.tempId) return
      qc.setQueryData<ChatMessage[]>(messagesQueryKey(variables.chatId), (prev) =>
        prev?.filter((m) => m.id !== context.tempId) ?? [],
      )
      onErrorToast?.(userFacingMessageFromUnknown(_err))
    },
  })
}
