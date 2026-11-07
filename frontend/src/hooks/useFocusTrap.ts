import { type RefObject, useEffect } from 'react'

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'

/**
 * Tab-focus-trap внутри контейнера диалога (portal): Tab/Shift+Tab зацикливаются
 * между первым и последним фокусируемым элементом, фокус не уходит на фон.
 */
export function useFocusTrap(containerRef: RefObject<HTMLElement | null>, enabled = true) {
  useEffect(() => {
    const el = containerRef.current
    if (!el || !enabled) return
    function onKey(e: KeyboardEvent) {
      if (e.key !== 'Tab') return
      const root = containerRef.current
      if (!root) return
      const focusable = root.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)
      if (focusable.length === 0) return
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (e.shiftKey) {
        if (document.activeElement === first || !root.contains(document.activeElement)) {
          e.preventDefault()
          last.focus()
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault()
          first.focus()
        }
      }
    }
    el.addEventListener('keydown', onKey)
    return () => el.removeEventListener('keydown', onKey)
  }, [containerRef, enabled])
}
