import { useEffect, type RefObject } from 'react'

import {
  applyClassicScrollbarInsetVar,
  classicScrollbarInsetPx,
} from '@/utils/layout/classicScrollbarInset'

function syncClassicScrollbarInset(el: HTMLElement): void {
  applyClassicScrollbarInsetVar(
    el.style,
    classicScrollbarInsetPx(el.offsetWidth, el.clientWidth),
  )
}

/**
 * Когда у контейнера появляется классический скроллбар, уменьшает правый padding
 * на его ширину — ширина текста не прыгает, пустой gutter не резервируется.
 */
export function useClassicScrollbarInset(
  scrollRef: RefObject<HTMLElement | null>,
  enabled: boolean,
  resyncKey?: string,
): void {
  useEffect(() => {
    const el = scrollRef.current
    if (!el || !enabled) {
      if (el) {
        applyClassicScrollbarInsetVar(el.style, 0)
      }
      return
    }

    let raf = 0
    const schedule = () => {
      if (raf !== 0) {
        return
      }
      raf = window.requestAnimationFrame(() => {
        raf = 0
        const current = scrollRef.current
        if (current) {
          syncClassicScrollbarInset(current)
        }
      })
    }

    schedule()
    const ro = new ResizeObserver(schedule)
    ro.observe(el)
    const child = el.firstElementChild
    if (child) {
      ro.observe(child)
    }
    window.addEventListener('resize', schedule)

    return () => {
      window.removeEventListener('resize', schedule)
      ro.disconnect()
      if (raf !== 0) {
        window.cancelAnimationFrame(raf)
      }
      applyClassicScrollbarInsetVar(el.style, 0)
    }
  }, [scrollRef, enabled, resyncKey])
}
