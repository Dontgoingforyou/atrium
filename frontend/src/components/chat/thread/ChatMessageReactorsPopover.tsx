import { createPortal } from 'react-dom'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'

import { getMessageReactionReactors } from '../../../api/chat/chatApi'
import { messageReactorsQueryKey } from '../../../api/queryKeys'
import { timeOnly } from '@/utils/chat/chatDate'
import {
  audiencePopoverStyle,
  type AudienceAnchorRect,
} from '@/utils/chat/audiencePopoverPos'
import { userFacingMessageFromUnknown } from '../../../utils/apiUserMessage'
import overlay from '@/styles/modules/chat/ChatMessageListOverlays.module.css'

type Props = {
  chatId: string
  messageId: string
  emoji: string
  anchorRect: AudienceAnchorRect
  userMap: Record<string, string>
  currentUserSub: string | null
  busy: boolean
  onClose: () => void
  onToggleReaction: (messageId: string, emoji: string) => Promise<void>
}

export function ChatMessageReactorsPopover({
  chatId,
  messageId,
  emoji,
  anchorRect,
  userMap,
  currentUserSub,
  busy,
  onClose,
  onToggleReaction,
}: Props) {
  const [toggleError, setToggleError] = useState<string | null>(null)
  const [toggling, setToggling] = useState(false)
  const { data, isPending, isError } = useQuery({
    queryKey: messageReactorsQueryKey(chatId, messageId, emoji),
    queryFn: () => getMessageReactionReactors(chatId, messageId, emoji),
    staleTime: 10_000,
  })

  const mine = (data ?? []).some((r) => r.user_sub === currentUserSub)
  const actionBusy = busy || toggling

  return createPortal(
    <div
      role="presentation"
      className={overlay.readersPopoverOverlay}
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-label="Кто поставил реакцию"
        className={overlay.readersPopover}
        style={audiencePopoverStyle(anchorRect, 240)}
        onClick={(e) => e.stopPropagation()}
      >
        <div className={overlay.readersPopoverTitle}>Реакция {emoji}</div>
        {isPending ? (
          <div className={overlay.readersPopoverEmpty}>Загрузка…</div>
        ) : isError ? (
          <div className={overlay.readersPopoverEmpty}>Не удалось загрузить</div>
        ) : !data || data.length === 0 ? (
          <div className={overlay.readersPopoverEmpty}>Пока никого</div>
        ) : (
          data.map((r) => (
            <div key={r.user_sub} className={overlay.readersPopoverRow}>
              <span className={overlay.readersPopoverName}>
                {userMap[r.user_sub] ?? '...'}
              </span>
              <span className={overlay.readersPopoverTime}>{timeOnly(r.reacted_at)}</span>
            </div>
          ))
        )}
        {toggleError ? <div className={overlay.reactorsToggleError}>{toggleError}</div> : null}
        <button
          type="button"
          className={overlay.reactorsToggleBtn}
          disabled={actionBusy}
          onClick={() => {
            setToggleError(null)
            setToggling(true)
            void onToggleReaction(messageId, emoji)
              .then(() => {
                onClose()
              })
              .catch((e: unknown) => {
                setToggleError(userFacingMessageFromUnknown(e))
              })
              .finally(() => {
                setToggling(false)
              })
          }}
        >
          {mine ? 'Снять реакцию' : 'Поставить такую же'}
        </button>
      </div>
    </div>,
    document.body,
  )
}
