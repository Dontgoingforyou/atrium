import type { QueryClient } from '@tanstack/react-query'

import { markChatRead } from '../../api/chat/chatApi'
import { patchPortalChatUnreadZero } from '../../utils/chat/patchPortalChatsUnread'

export function markChatReadAndPatchUnread(qc: QueryClient, chatId: string): void {
  void markChatRead(chatId)
    .then(() => patchPortalChatUnreadZero(qc, chatId))
    .catch(() => {
      /* отметка прочитанного — не критична; без тоста, чтобы не шуметь */
    })
}
