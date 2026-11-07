import { useLayoutEffect, useState, type RefObject } from 'react'

import {
  clampHorizontalLeft,
  computeAnchoredMenuPlacement,
} from './dropdownPlacement'

const MENU_ESTIMATED_HEIGHT = 200

export interface AnchoredMenuPosition {
  top: number
  left: number
  maxHeight: number
  openUp: boolean
}

/** Позиция выпадающего меню у правого края якоря (portal, fixed). */
export function useAnchoredMenuPosition(
  open: boolean,
  anchorRef: RefObject<Element | null>,
  menuWidth: number,
  menuRef?: RefObject<Element | null>,
): AnchoredMenuPosition {
  const [pos, setPos] = useState<AnchoredMenuPosition>({
    top: 0,
    left: 0,
    maxHeight: MENU_ESTIMATED_HEIGHT,
    openUp: false,
  })

  useLayoutEffect(() => {
    if (!open) return

    function recalc() {
      const el = anchorRef.current
      if (!el) return
      const rect = el.getBoundingClientRect()
      const left = clampHorizontalLeft(rect, menuWidth, window.innerWidth)
      const menuHeight = menuRef?.current?.getBoundingClientRect().height ?? MENU_ESTIMATED_HEIGHT
      const placement = computeAnchoredMenuPlacement(rect, window.innerHeight, menuHeight)
      setPos({ top: placement.top, left, maxHeight: placement.maxHeight, openUp: placement.openUp })
    }

    recalc()
    const rafId = requestAnimationFrame(() => {
      recalc()
      const menuEl = menuRef?.current
      if (menuEl && ro) {
        ro.observe(menuEl)
      }
    })
    window.addEventListener('scroll', recalc, true)
    window.addEventListener('resize', recalc)

    const menuEl = menuRef?.current
    const ro = menuEl ? new ResizeObserver(recalc) : null
    if (menuEl && ro) {
      ro.observe(menuEl)
    }

    return () => {
      cancelAnimationFrame(rafId)
      window.removeEventListener('scroll', recalc, true)
      window.removeEventListener('resize', recalc)
      ro?.disconnect()
    }
  }, [open, anchorRef, menuWidth, menuRef])

  return pos
}
