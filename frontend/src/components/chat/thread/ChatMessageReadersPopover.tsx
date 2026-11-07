import { createPortal } from 'react-dom'
import { useQuery } from '@tanstack/react-query'

import { getMessageReaders } from '../../../api/chat/chatApi'
import { messageReadersQueryKey } from '../../../api/queryKeys'
import { timeOnly } from '@/utils/chat/chatDate'
import {
  audiencePopoverStyle,
  type AudienceAnchorRect,
} from '@/utils/chat/audiencePopoverPos'
import overlay from '@/styles/modules/chat/ChatMessageListOverlays.module.css'

type Props = {
  chatId: string
  messageId: string
  anchorRect: AudienceAnchorRect
  userMap: Record<string, string>
  onClose: () => void
}

export function ChatMessageReadersPopover({
  chatId,
  messageId,
  anchorRect,
  userMap,
  onClose,
}: Props) {
  const { data, isPending, isError } = useQuery({
    queryKey: messageReadersQueryKey(chatId, messageId),
    queryFn: () => getMessageReaders(chatId, messageId),
    staleTime: 10_000,
  })

  return createPortal(
    <div
      role="presentation"
      className={overlay.readersPopoverOverlay}
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-label="Кто прочитал"
        className={overlay.readersPopover}
        style={audiencePopoverStyle(anchorRect, 220)}
        onClick={(e) => e.stopPropagation()}
      >
        <div className={overlay.readersPopoverTitle}>Прочитали</div>
        {isPending ? (
          <div className={overlay.readersPopoverEmpty}>Загрузка…</div>
        ) : isError ? (
          <div className={overlay.readersPopoverEmpty}>Не удалось загрузить</div>
        ) : !data || data.length === 0 ? (
          <div className={overlay.readersPopoverEmpty}>Никто ещё не прочитал</div>
        ) : (
          data.map((r) => (
            <div key={r.user_sub} className={overlay.readersPopoverRow}>
              <span className={overlay.readersPopoverName}>
                {userMap[r.user_sub] ?? '...'}
              </span>
              <span className={overlay.readersPopoverTime}>{timeOnly(r.read_at)}</span>
            </div>
          ))
        )}
      </div>
    </div>,
    document.body,
  )
}
