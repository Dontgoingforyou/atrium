import type { QueryClient } from '@tanstack/react-query'

import { PORTAL_CHATS_ALL_QUERY_KEY } from '../../api/queryKeys'
import type { Chat } from '../../types/chat'

/**
 * Обнуляет счётчик непрочитанных для чата в кэше без GET /portal/chats
 * (иначе на каждом прочтении заново подписываются все avatar_url и мерцают аватарки).
 */
export function patchPortalChatUnreadZero(qc: QueryClient, chatId: string): void {
  qc.setQueryData<Chat[]>(PORTAL_CHATS_ALL_QUERY_KEY, (prev) => {
    if (!prev) return prev
    return prev.map((c) => (c.id === chatId ? { ...c, unread_count: 0 } : c))
  })
}
