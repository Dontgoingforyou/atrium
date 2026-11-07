import { useCallback, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import { markChatRead } from '../api/chat/chatApi'
import { patchPortalChatUnreadZero } from '../utils/chat/patchPortalChatsUnread'

/** Throttle между двумя вызовами markChatRead по активности пользователя (мс). */
const CHAT_ACTIVITY_THROTTLE_MS = 1_500

/**
 * Возвращает callback `onChatActivity`, который нужно вешать на onMouseMove
 * панели чата. Если в активном чате есть непрочитанные — помечает его
 * прочитанным не чаще одного раза в CHAT_ACTIVITY_THROTTLE_MS.
 */
export function useChatActivityRead(
  activeChatId: string | null,
  unreadCount: number,
): () => void {
  const qc = useQueryClient()
  const throttleRef = useRef<number>(0)

  return useCallback(() => {
    if (!activeChatId || unreadCount === 0) return
    const now = Date.now()
    if (now - throttleRef.current < CHAT_ACTIVITY_THROTTLE_MS) return
    throttleRef.current = now
    void markChatRead(activeChatId)
      .then(() => patchPortalChatUnreadZero(qc, activeChatId))
      .catch(() => {
        /* сеть / 401 — тихо; следующий тик активности ретраит */
      })
  }, [activeChatId, unreadCount, qc])
}
