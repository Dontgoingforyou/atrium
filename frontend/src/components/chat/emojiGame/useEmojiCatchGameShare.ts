import { useCallback, useState } from 'react'
import { useMutation, useQueryClient, type QueryKey } from '@tanstack/react-query'

import { postMessage } from '../../../api/chat/chatApi'
import { PORTAL_CHATS_ALL_QUERY_KEY } from '../../../api/queryKeys'
import type { ChatMessage } from '../../../types/chat'
import { formatEmojiGameScoreMessage } from '@/utils/chat/emojiOnlyMessage'
import { userFacingMessageFromUnknown } from '../../../utils/apiUserMessage'
import { invalidatePortalSearchQueries } from '@/utils/search/invalidatePortalSearch'

type EmojiGameSession = {
  emojis: string[]
  sessionId: string
}

type Args = {
  chatId: string
  isDirect: boolean
  currentUserSub: string | null
  messagesCacheKey: QueryKey
}

export function useEmojiCatchGameShare({
  chatId,
  isDirect,
  currentUserSub,
  messagesCacheKey,
}: Args) {
  const qc = useQueryClient()
  const [emojiGame, setEmojiGame] = useState<EmojiGameSession | null>(null)
  const [shareError, setShareError] = useState<string | null>(null)

  const shareScoreMut = useMutation({
    mutationFn: ({ body }: { body: string }) => postMessage(chatId, { body }),
    onMutate: async ({ body }) => {
      setShareError(null)
      if (!currentUserSub) return { tempId: null as string | null }
      const tempId = `optimistic-${crypto.randomUUID()}`
      const tempMsg: ChatMessage = {
        id: tempId,
        chat_id: chatId,
        author_sub: currentUserSub,
        body,
        created_at: new Date().toISOString(),
        updated_at: null,
        deleted_for_all_at: null,
        receipt: 'sent',
      }
      await qc.cancelQueries({ queryKey: messagesCacheKey })
      qc.setQueryData<ChatMessage[]>(messagesCacheKey, (prev) =>
        prev ? [...prev, tempMsg] : [tempMsg],
      )
      return { tempId }
    },
    onSuccess: (newMsg, _vars, context) => {
      qc.setQueryData<ChatMessage[]>(messagesCacheKey, (prev) => {
        if (!prev) return [newMsg]
        const withoutTemp = context?.tempId ? prev.filter((m) => m.id !== context.tempId) : prev
        if (withoutTemp.some((m) => m.id === newMsg.id)) {
          return withoutTemp.map((m) => (m.id === newMsg.id ? newMsg : m))
        }
        return [...withoutTemp, newMsg]
      })
      void qc.invalidateQueries({ queryKey: PORTAL_CHATS_ALL_QUERY_KEY })
      invalidatePortalSearchQueries(qc)
      setEmojiGame(null)
      setShareError(null)
    },
    onError: (err, _vars, context) => {
      if (context?.tempId) {
        qc.setQueryData<ChatMessage[]>(messagesCacheKey, (prev) =>
          prev?.filter((m) => m.id !== context.tempId) ?? [],
        )
      }
      setShareError(userFacingMessageFromUnknown(err))
    },
  })

  const openEmojiGame = useCallback((emojis: string[]) => {
    setShareError(null)
    setEmojiGame({ emojis, sessionId: crypto.randomUUID() })
  }, [])

  const closeEmojiGame = useCallback(() => {
    if (shareScoreMut.isPending) return
    setEmojiGame(null)
    setShareError(null)
  }, [shareScoreMut.isPending])

  const shareScore = useCallback(
    (score: number) => {
      if (!isDirect || !emojiGame) return
      const emoji = emojiGame.emojis[0] ?? '😀'
      shareScoreMut.mutate({ body: formatEmojiGameScoreMessage(emoji, score) })
    },
    [emojiGame, isDirect, shareScoreMut],
  )

  return {
    emojiGame,
    shareError,
    sharePending: shareScoreMut.isPending,
    openEmojiGame,
    closeEmojiGame,
    shareScore,
  }
}
