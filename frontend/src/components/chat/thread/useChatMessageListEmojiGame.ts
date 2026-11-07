import { useEffect } from 'react'

import type { ChatMessage } from '../../../types/chat'

import { useEmojiCatchGameShare } from '../emojiGame/useEmojiCatchGameShare'
import { bestEmojiGameScoresByAuthor } from '@/utils/chat/emojiOnlyMessage'
import type { useEmojiPongOnline } from '@/hooks/useEmojiPongOnline'

type EmojiPong = ReturnType<typeof useEmojiPongOnline> | null

type Args = {
  chatId: string
  isDirect: boolean
  currentUserSub: string | null
  messages: ChatMessage[]
  messagesQueryKey?: readonly unknown[]
  peerUserSub?: string | null
  userMap: Record<string, string>
  userAvatarBySub: Record<string, string | undefined>
  emojiPong: EmojiPong
}

/**
 * Интеграция emoji-игры в ленту сообщений DM: состояние пасхалки
 * (useEmojiCatchGameShare), расчёт игроков табло (я / собеседник) и
 * авто-открытие игры по входящему инвайту / гостевой сессии emoji-pong.
 *
 * Рендер модалки остаётся в {@link ChatMessageList}; здесь только данные.
 */
export function useChatMessageListEmojiGame({
  chatId,
  isDirect,
  currentUserSub,
  messages,
  messagesQueryKey,
  peerUserSub,
  userMap,
  userAvatarBySub,
  emojiPong,
}: Args) {
  const messagesCacheKey = messagesQueryKey ?? (['portal', 'messages', chatId] as const)
  const {
    emojiGame,
    shareError,
    sharePending,
    openEmojiGame,
    closeEmojiGame,
    shareScore,
  } = useEmojiCatchGameShare({
    chatId,
    isDirect,
    currentUserSub,
    messagesCacheKey,
  })

  const bestScores = bestEmojiGameScoresByAuthor(messages)
  const resolvedPeerSub =
    peerUserSub
    ?? (currentUserSub
      ? messages.find((m) => m.author_sub !== currentUserSub)?.author_sub ?? null
      : null)
  const peerPlayer = {
    label: resolvedPeerSub ? (userMap[resolvedPeerSub] ?? 'Собеседник') : 'Собеседник',
    imageUrl: resolvedPeerSub ? userAvatarBySub[resolvedPeerSub] : undefined,
    bestScore: resolvedPeerSub ? (bestScores[resolvedPeerSub] ?? 0) : 0,
  }
  const mePlayer = {
    label: currentUserSub ? (userMap[currentUserSub] ?? 'Вы') : 'Вы',
    imageUrl: currentUserSub ? userAvatarBySub[currentUserSub] : undefined,
    bestScore: currentUserSub ? (bestScores[currentUserSub] ?? 0) : 0,
  }

  useEffect(() => {
    if (!emojiPong?.incomingInvite) return
    if (emojiGame) return
    openEmojiGame([emojiPong.incomingInvite.emoji])
  }, [emojiGame, emojiPong?.incomingInvite, openEmojiGame])

  useEffect(() => {
    if (!emojiPong?.liveSession?.playing || emojiPong.liveSession.role !== 'guest') return
    if (emojiGame) return
    openEmojiGame([emojiPong.liveSession.emoji])
  }, [emojiGame, emojiPong?.liveSession, openEmojiGame])

  return {
    emojiGame,
    shareError,
    sharePending,
    openEmojiGame,
    closeEmojiGame,
    shareScore,
    peerPlayer,
    mePlayer,
  }
}
