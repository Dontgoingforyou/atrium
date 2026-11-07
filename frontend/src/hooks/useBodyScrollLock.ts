import { useEffect } from 'react'

/**
 * Блокирует скролл body пока диалог открыт, с компенсацией ширины скроллбара
 * (чтобы контент не дёргался при появлении/исчезновении overlay).
 *
 * Поддерживает вложенные overlay (Modal + Lightbox и т.п.): модульный счётчик
 * активных блокировк — `overflow: hidden` ставится при 0→1, снимается при 1→0,
 * поэтому unmount внутреннего overlay не снимает lock раньше внешнего.
 */
let activeLocks = 0
let savedOverflow = ''
let savedPaddingRight = ''

export function useBodyScrollLock(enabled = true) {
  useEffect(() => {
    if (!enabled) return
    const isFirst = activeLocks === 0
    activeLocks += 1

    if (isFirst) {
      savedOverflow = document.body.style.overflow
      savedPaddingRight = document.body.style.paddingRight
      const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth
      document.body.style.overflow = 'hidden'
      if (scrollbarWidth > 0) {
        document.body.style.paddingRight = `${scrollbarWidth}px`
      }
    }

    return () => {
      activeLocks = Math.max(0, activeLocks - 1)
      if (activeLocks === 0) {
        document.body.style.overflow = savedOverflow
        document.body.style.paddingRight = savedPaddingRight
      }
    }
  }, [enabled])
}
