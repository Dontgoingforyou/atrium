import { useLayoutEffect, useState, type RefObject } from 'react'

import {
  DROPDOWN_DEFAULT_MAX_HEIGHT,
  computeVerticalDropdownPlacement,
  type VerticalPlacement,
} from './dropdownPlacement'

export interface DropdownPosition extends VerticalPlacement {
  left: number
  width: number
}

/**
 * Вычисляет и обновляет позицию выпадающего списка (portal) в viewport-координатах.
 *
 * @param open          - открыт ли dropdown
 * @param anchorRef     - реф кнопки/инпута, к которому прикрепляется список
 * @param maxHeight     - максимальная высота dropdown (по умолчанию 280)
 * @returns позиция `{ top, left, width, maxHeight }` в px
 */
export function useDropdownPosition(
  open: boolean,
  anchorRef: RefObject<Element | null>,
  maxHeight = DROPDOWN_DEFAULT_MAX_HEIGHT,
  minDropdownWidth?: number,
): DropdownPosition {
  const [pos, setPos] = useState<DropdownPosition>({
    top: 0,
    left: 0,
    width: 0,
    maxHeight,
    openUp: false,
  })

  useLayoutEffect(() => {
    if (!open) return

    function recalc() {
      if (!anchorRef.current) return
      const rect = anchorRef.current.getBoundingClientRect()
      const width = Math.max(rect.width, minDropdownWidth ?? 200)
      const placement = computeVerticalDropdownPlacement(rect, window.innerHeight, maxHeight)
      setPos({ ...placement, left: rect.left, width })
    }

    recalc()
    window.addEventListener('scroll', recalc, true)
    window.addEventListener('resize', recalc)
    return () => {
      window.removeEventListener('scroll', recalc, true)
      window.removeEventListener('resize', recalc)
    }
  }, [open, maxHeight, minDropdownWidth, anchorRef])

  return pos
}
