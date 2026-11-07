import { useEffect, useLayoutEffect, useRef, type RefObject } from 'react'

const STORAGE_PREFIX = 'cosmolet.kanban.scroll.'

/** Сохраняет горизонтальный scroll канбана в sessionStorage между перезагрузками. */
export function useKanbanScrollPersist(
  scrollRef: RefObject<HTMLElement | null>,
  storageKey: string,
  ready: boolean,
  /** false — не восстанавливать сохранённую позицию (доска сама прокрутится к нужной колонке). */
  restore = true,
) {
  const restoredRef = useRef(false)
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useLayoutEffect(() => {
    if (!ready || restoredRef.current) return
    const el = scrollRef.current
    if (!el) return

    const raw = restore ? sessionStorage.getItem(STORAGE_PREFIX + storageKey) : null
    if (raw) {
      const left = Number.parseInt(raw, 10)
      if (Number.isFinite(left) && left >= 0) {
        const apply = () => {
          const node = scrollRef.current
          if (!node) return
          const max = Math.max(0, node.scrollWidth - node.clientWidth)
          node.scrollLeft = Math.min(left, max)
        }
        apply()
        requestAnimationFrame(apply)
      }
    }
    restoredRef.current = true
  }, [ready, restore, scrollRef, storageKey])

  // Страхуем ref-timing: если scrollRef.current был null при ready=true,
  // restore не сработал (restoredRef остался false). Повторяем на следующем кадре.
  useLayoutEffect(() => {
    if (!ready || restoredRef.current) return
    if (scrollRef.current) return // уже обработано выше или будет
    const rafId = requestAnimationFrame(() => {
      if (restoredRef.current) return
      const el = scrollRef.current
      if (!el) return
      const raw = restore ? sessionStorage.getItem(STORAGE_PREFIX + storageKey) : null
      if (raw) {
        const left = Number.parseInt(raw, 10)
        if (Number.isFinite(left) && left >= 0) {
          const max = Math.max(0, el.scrollWidth - el.clientWidth)
          el.scrollLeft = Math.min(left, max)
        }
      }
      restoredRef.current = true
    })
    return () => cancelAnimationFrame(rafId)
  }, [ready, restore, scrollRef, storageKey])

  useEffect(() => {
    if (!ready) return
    const el = scrollRef.current
    if (!el) return

    const onScroll = () => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current)
      saveTimerRef.current = setTimeout(() => {
        sessionStorage.setItem(STORAGE_PREFIX + storageKey, String(el.scrollLeft))
      }, 150)
    }

    el.addEventListener('scroll', onScroll, { passive: true })
    return () => {
      el.removeEventListener('scroll', onScroll)
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current)
    }
  }, [ready, scrollRef, storageKey])
}
