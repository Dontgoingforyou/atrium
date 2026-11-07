import { useCallback, useEffect, useRef, useState } from 'react'

export type UseRightDrawerReturn = {
  open: boolean
  entered: boolean
  openDrawer: () => void
  closeDrawer: () => void
  onTransitionEnd: (e: React.TransitionEvent<HTMLElement>) => void
}

/**
 * Состояние правого drawer: open/entered + анимация + Escape.
 *
 * `onClosed` вызывается, когда drawer действительно закрыт (сразу при instant-закрытии
 * для `prefers-reduced-motion`, иначе — по завершении transform-перехода). Контроллеры
 * чистят связанное состояние (выбранный тег и т.п.) в нём, не дублируя проверку
 * `matchMedia('(prefers-reduced-motion: reduce)')` — единый источник правды здесь.
 */
export function useRightDrawer(onClosed?: () => void): UseRightDrawerReturn {
  const [open, setOpen] = useState(false)
  const [entered, setEntered] = useState(false)
  const onClosedRef = useRef(onClosed)
  useEffect(() => {
    onClosedRef.current = onClosed
  }, [onClosed])

  useEffect(() => {
    if (!open) return
    const id = window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => setEntered(true))
    })
    return () => window.cancelAnimationFrame(id)
  }, [open])

  const closeDrawer = useCallback(() => {
    const instant =
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    setEntered(false)
    if (instant) {
      setOpen(false)
      onClosedRef.current?.()
    }
  }, [])

  useEffect(() => {
    if (!open) return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') closeDrawer()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, closeDrawer])

  const openDrawer = useCallback(() => {
    setEntered(false)
    setOpen(true)
  }, [])

  const onTransitionEnd = useCallback(
    (e: React.TransitionEvent<HTMLElement>) => {
      if (e.target !== e.currentTarget || e.propertyName !== 'transform') return
      if (!entered) {
        setOpen(false)
        onClosedRef.current?.()
      }
    },
    [entered],
  )

  return { open, entered, openDrawer, closeDrawer, onTransitionEnd }
}
