import { Suspense, lazy } from 'react'
import { createPortal } from 'react-dom'

import styles from '@/styles/modules/chat/MessageInput.module.css'

const MessageInputEmojiPanel = lazy(() => import('./MessageInputEmojiPanel'))

type Props = {
  emojiOpen: boolean
  emojiInPortal: boolean
  emojiPickerPos: { top: number; left: number; width: number; maxHeight: number }
  emojiPickerPortalRef: React.RefObject<HTMLDivElement | null>
  theme: 'dark' | 'light'
  onEmojiSelect: (e: { native: string }) => void
}

function PickerFallback() {
  return (
    <div className={styles.pickerFallback} role="status" aria-live="polite">
      Загрузка панели…
    </div>
  )
}

/**
 * Рендер emoji-панели композера: инлайн (variant default/panel) или в portal
 * (variant widget — узкая панель). Состояние/позиционирование — в
 * {@link useMessageInputEmojiPicker}.
 */
export function MessageInputEmojiPicker({
  emojiOpen,
  emojiInPortal,
  emojiPickerPos,
  emojiPickerPortalRef,
  theme,
  onEmojiSelect,
}: Props) {
  if (!emojiOpen) return null

  if (!emojiInPortal) {
    return (
      <div className={styles.pickerWrap}>
        <Suspense fallback={<PickerFallback />}>
          <MessageInputEmojiPanel theme={theme} onEmojiSelect={onEmojiSelect} />
        </Suspense>
      </div>
    )
  }

  return createPortal(
    <div
      ref={emojiPickerPortalRef}
      data-emoji-picker-portal
      className={styles.pickerWrapPortal}
      style={{
        top: emojiPickerPos.top,
        left: emojiPickerPos.left,
        width: emojiPickerPos.width,
        maxHeight: emojiPickerPos.maxHeight,
      }}
    >
      <Suspense fallback={<PickerFallback />}>
        <MessageInputEmojiPanel theme={theme} onEmojiSelect={onEmojiSelect} />
      </Suspense>
    </div>,
    document.body,
  )
}
