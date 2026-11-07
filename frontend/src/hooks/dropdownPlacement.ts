export const DROPDOWN_GAP = 4
export const DROPDOWN_SCREEN_MARGIN = 8
export const DROPDOWN_MIN_VISIBLE_HEIGHT = 120
export const DROPDOWN_DEFAULT_MAX_HEIGHT = 280
export const DROPDOWN_FLIP_THRESHOLD = 160

export interface VerticalPlacement {
  top: number
  maxHeight: number
  openUp: boolean
}

/** Вертикальное размещение dropdown с заданной предпочтительной max-height (SearchablePicker и т.п.). */
export function computeVerticalDropdownPlacement(
  anchorRect: DOMRect,
  viewportHeight: number,
  preferredMaxHeight: number,
  options?: {
    gap?: number
    screenMargin?: number
    minVisibleHeight?: number
    flipThreshold?: number
  },
): VerticalPlacement {
  const gap = options?.gap ?? DROPDOWN_GAP
  const screenMargin = options?.screenMargin ?? DROPDOWN_SCREEN_MARGIN
  const minVisibleHeight = options?.minVisibleHeight ?? DROPDOWN_MIN_VISIBLE_HEIGHT
  const flipThreshold = options?.flipThreshold ?? DROPDOWN_FLIP_THRESHOLD

  const spaceBelow = viewportHeight - anchorRect.bottom - screenMargin
  const spaceAbove = anchorRect.top - screenMargin
  const openUp = spaceBelow < flipThreshold && spaceAbove > spaceBelow
  const maxHeight = Math.min(
    preferredMaxHeight,
    Math.max(minVisibleHeight, openUp ? spaceAbove : spaceBelow),
  )
  const top = openUp ? anchorRect.top - maxHeight - gap : anchorRect.bottom + gap

  return { top, maxHeight, openUp }
}

/** Вертикальное размещение anchored-меню с известной (или оценочной) высотой. */
export function computeAnchoredMenuPlacement(
  anchorRect: DOMRect,
  viewportHeight: number,
  menuHeight: number,
  options?: {
    gap?: number
    screenMargin?: number
    minVisibleHeight?: number
  },
): VerticalPlacement {
  const gap = options?.gap ?? DROPDOWN_GAP
  const screenMargin = options?.screenMargin ?? DROPDOWN_SCREEN_MARGIN
  const minVisibleHeight = options?.minVisibleHeight ?? DROPDOWN_MIN_VISIBLE_HEIGHT

  const spaceBelow = viewportHeight - anchorRect.bottom - screenMargin
  const spaceAbove = anchorRect.top - screenMargin

  const fitsBelow = menuHeight <= spaceBelow
  const fitsAbove = menuHeight <= spaceAbove

  if (fitsBelow || (!fitsAbove && spaceBelow >= spaceAbove)) {
    return {
      top: anchorRect.bottom + gap,
      maxHeight: fitsBelow ? menuHeight : Math.max(minVisibleHeight, spaceBelow),
      openUp: false,
    }
  }

  const maxHeight = fitsAbove ? menuHeight : Math.max(minVisibleHeight, spaceAbove)
  return {
    top: anchorRect.top - maxHeight - gap,
    maxHeight,
    openUp: true,
  }
}

export function clampHorizontalLeft(
  anchorRect: DOMRect,
  menuWidth: number,
  viewportWidth: number,
  screenMargin = DROPDOWN_SCREEN_MARGIN,
): number {
  return Math.min(
    Math.max(screenMargin, anchorRect.right - menuWidth),
    viewportWidth - menuWidth - screenMargin,
  )
}
