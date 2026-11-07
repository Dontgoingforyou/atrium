import { useCallback, useLayoutEffect, useRef, useState, type RefObject } from 'react'

import { useClickOutside } from '../../../hooks/useClickOutside'

import { EMOJI_PICKER_MAX_HEIGHT } from './messageInputTypes'

type EmojiPickerPos = {
  top: number
  left: number
  width: number
  maxHeight: number
}

type Args = {
  variant: 'default' | 'panel' | 'widget'
  textareaRef: RefObject<HTMLTextAreaElement | null>
  setValue: React.Dispatch<React.SetStateAction<string>>
}

/**
 * Состояние и позиционирование emoji-панели композера: признак открытия,
 * координаты портальной панели (variant='widget'), click-outside, вставка
 * выбранного эмодзи в каретку textarea. Сам рендер панели — в
 * {@link MessageInputEmojiPicker}.
 */
export function useMessageInputEmojiPicker({ variant, textareaRef, setValue }: Args) {
  const [emojiOpen, setEmojiOpen] = useState(false)
  const [emojiPickerPos, setEmojiPickerPos] = useState<EmojiPickerPos>({
    top: 0,
    left: 0,
    width: 320,
    maxHeight: EMOJI_PICKER_MAX_HEIGHT,
  })
  const popoverRef = useRef<HTMLDivElement>(null)
  const emojiPickerPortalRef = useRef<HTMLDivElement>(null)

  const emojiInPortal = variant === 'widget'

  const calcEmojiPickerPosition = useCallback(() => {
    if (!popoverRef.current) return
    const rect = popoverRef.current.getBoundingClientRect()
    const width = Math.min(360, Math.max(rect.width, 280), window.innerWidth - 16)
    const maxHeight = Math.min(EMOJI_PICKER_MAX_HEIGHT, Math.max(200, rect.top - 12))
    const left = Math.min(Math.max(8, rect.left), window.innerWidth - width - 8)
    const top = Math.max(8, rect.top - maxHeight - 6)
    setEmojiPickerPos({ top, left, width, maxHeight })
  }, [])

  useLayoutEffect(() => {
    if (!emojiOpen || !emojiInPortal) return
    calcEmojiPickerPosition()
    window.addEventListener('resize', calcEmojiPickerPosition)
    window.addEventListener('scroll', calcEmojiPickerPosition, true)
    return () => {
      window.removeEventListener('resize', calcEmojiPickerPosition)
      window.removeEventListener('scroll', calcEmojiPickerPosition, true)
    }
  }, [emojiOpen, emojiInPortal, calcEmojiPickerPosition])

  useClickOutside(emojiOpen, [popoverRef, emojiPickerPortalRef], () => setEmojiOpen(false), 'mousedown')

  const insertAtCursor = useCallback(
    (text: string) => {
      const el = textareaRef.current
      if (!el) {
        setValue((v) => v + text)
        return
      }
      const start = el.selectionStart
      const end = el.selectionEnd
      setValue((v) => v.slice(0, start) + text + v.slice(end))
      requestAnimationFrame(() => {
        const pos = start + text.length
        el.focus({ preventScroll: true })
        el.setSelectionRange(pos, pos)
      })
    },
    [textareaRef, setValue],
  )

  return {
    emojiOpen,
    setEmojiOpen,
    emojiPickerPos,
    emojiInPortal,
    popoverRef,
    emojiPickerPortalRef,
    calcEmojiPickerPosition,
    insertAtCursor,
  }
}
