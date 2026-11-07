export async function waitForTourTarget(
  selector: string,
  timeoutMs = 2500,
  pollMs = 80,
): Promise<Element | null> {
  if (typeof document === 'undefined') return null
  const started = Date.now()
  for (;;) {
    const el = document.querySelector(selector)
    if (el) return el
    if (Date.now() - started >= timeoutMs) return null
    await new Promise((r) => setTimeout(r, pollMs))
  }
}

export type PopoverPlacement = 'top' | 'bottom' | 'left' | 'right'

export type RectLike = {
  top: number
  left: number
  right: number
  bottom: number
  width: number
  height: number
}

/** Совпадает с PAD в TourSpotlight — плашка не должна наезжать на обводку. */
export const TOUR_SPOTLIGHT_PAD = 6
const GAP_TB = 16
/** Отступ слева/справа от якоря (с учётом обводки spotlight). */
const GAP_LR = 36
/** Совпадает с width попапа в GuidedTour.module.css. */
export const POPOVER_W = 400
/** Оценка высоты до измерения DOM; CSS max-height попапа — 360px. */
export const POPOVER_H = 320
/** Совпадает с --space-lg (токены нельзя читать из layout-математики без getComputedStyle). */
export const VIEWPORT_PAD = 16
const TALL_TARGET_RATIO = 0.45
const WIDE_TARGET_MIN_W = POPOVER_W * 2

function spaceFor(
  target: RectLike,
  viewport: { width: number; height: number },
): Record<PopoverPlacement, number> {
  return {
    top: target.top,
    bottom: viewport.height - target.bottom,
    left: target.left,
    right: viewport.width - target.right,
  }
}

function minSpaceFor(placement: PopoverPlacement): number {
  if (placement === 'left' || placement === 'right') return POPOVER_W + GAP_LR
  return POPOVER_H + GAP_TB
}

function inflateTarget(target: RectLike, pad = TOUR_SPOTLIGHT_PAD): RectLike {
  return {
    top: target.top - pad,
    left: target.left - pad,
    right: target.right + pad,
    bottom: target.bottom + pad,
    width: target.width + pad * 2,
    height: target.height + pad * 2,
  }
}

export function pickPopoverPlacement(
  target: RectLike,
  viewport: { width: number; height: number },
  prefer?: PopoverPlacement,
): PopoverPlacement {
  const space = spaceFor(target, viewport)
  if (prefer && space[prefer] >= minSpaceFor(prefer)) {
    return prefer
  }
  const order: PopoverPlacement[] = ['bottom', 'top', 'right', 'left']
  let best: PopoverPlacement = 'bottom'
  let bestScore = -1
  for (const side of order) {
    const score = space[side]
    if (score > bestScore) {
      bestScore = score
      best = side
    }
  }
  return best
}

function rectsOverlap(
  a: { top: number; left: number; width: number; height: number },
  b: RectLike,
): boolean {
  return !(
    a.left + a.width <= b.left ||
    b.right <= a.left ||
    a.top + a.height <= b.top ||
    b.bottom <= a.top
  )
}

function horizontalOffsetForTb(hit: RectLike): number {
  if (hit.width >= WIDE_TARGET_MIN_W) {
    return hit.left
  }
  return hit.left + hit.width / 2 - POPOVER_W / 2
}

function positionBesideTarget(
  hit: RectLike,
  size: { width: number; height: number },
  viewport: { width: number; height: number },
): { top: number; left: number } {
  const leftSpace = hit.left
  const rightSpace = viewport.width - hit.right
  const need = size.width + VIEWPORT_PAD
  let left = VIEWPORT_PAD
  if (rightSpace >= leftSpace && rightSpace >= need) {
    left = hit.right + GAP_LR
  } else if (leftSpace >= need) {
    left = hit.left - GAP_LR - size.width
  } else if (rightSpace > leftSpace) {
    left = viewport.width - size.width - VIEWPORT_PAD
  }
  return clampPopoverInViewport({ top: VIEWPORT_PAD, left }, size, viewport)
}

export function fitPopoverAwayFromTarget(
  pos: { top: number; left: number },
  size: { width: number; height: number },
  viewport: { width: number; height: number },
  target: RectLike | null,
): { top: number; left: number } {
  const clamped = clampPopoverInViewport(pos, size, viewport)
  if (!target) return clamped
  const hit = inflateTarget(target)
  if (!rectsOverlap({ ...clamped, width: size.width, height: size.height }, hit)) {
    return clamped
  }
  if (hit.height >= viewport.height * TALL_TARGET_RATIO) {
    return positionBesideTarget(hit, size, viewport)
  }
  const above = clampPopoverInViewport(
    { top: hit.top - GAP_TB - size.height, left: clamped.left },
    size,
    viewport,
  )
  if (!rectsOverlap({ ...above, width: size.width, height: size.height }, hit)) {
    return above
  }
  return positionBesideTarget(hit, size, viewport)
}

/** Держит плашку целиком в viewport по фактическому размеру (ниже 2K высота часто меньше оценки). */
export function clampPopoverInViewport(
  pos: { top: number; left: number },
  size: { width: number; height: number },
  viewport: { width: number; height: number },
  pad = VIEWPORT_PAD,
): { top: number; left: number } {
  const maxTop = Math.max(pad, viewport.height - size.height - pad)
  const maxLeft = Math.max(pad, viewport.width - size.width - pad)
  return {
    top: Math.min(Math.max(pos.top, pad), maxTop),
    left: Math.min(Math.max(pos.left, pad), maxLeft),
  }
}

export function popoverPosition(
  target: RectLike,
  placement: PopoverPlacement,
  viewport: { width: number; height: number },
): { top: number; left: number } {
  const hit = inflateTarget(target)
  if (hit.height >= viewport.height * TALL_TARGET_RATIO) {
    return positionBesideTarget(hit, { width: POPOVER_W, height: POPOVER_H }, viewport)
  }
  const gap = placement === 'left' || placement === 'right' ? GAP_LR : GAP_TB
  let top = hit.bottom + gap
  let left = horizontalOffsetForTb(hit)
  if (placement === 'top') {
    top = hit.top - gap - POPOVER_H
  } else if (placement === 'left') {
    // Верх плашки ближе к верху якоря — меньше угол «наезжает» на иконку.
    top = hit.top
    left = hit.left - gap - POPOVER_W
  } else if (placement === 'right') {
    top = hit.top
    left = hit.right + gap
  }

  left = Math.max(VIEWPORT_PAD, Math.min(left, viewport.width - POPOVER_W - VIEWPORT_PAD))
  top = clampPopoverTop(top, viewport.height)

  const pop = { top, left, width: POPOVER_W, height: POPOVER_H }
  if (rectsOverlap(pop, hit)) {
    const upTop = clampPopoverTop(hit.top - GAP_TB - POPOVER_H, viewport.height)
    const upPop = { top: upTop, left, width: POPOVER_W, height: POPOVER_H }
    if (!rectsOverlap(upPop, hit)) {
      return { top: upTop, left }
    }
    if (hit.width >= WIDE_TARGET_MIN_W) {
      const aboveTop = hit.top - GAP_TB - POPOVER_H
      if (aboveTop >= VIEWPORT_PAD) {
        return { top: aboveTop, left }
      }
      return positionBesideTarget(hit, { width: POPOVER_W, height: POPOVER_H }, viewport)
    }
    left = Math.max(VIEWPORT_PAD, hit.left - GAP_LR - POPOVER_W)
    left = Math.max(VIEWPORT_PAD, Math.min(left, viewport.width - POPOVER_W - VIEWPORT_PAD))
    const again = { top, left, width: POPOVER_W, height: POPOVER_H }
    if (rectsOverlap(again, hit)) {
      top = clampPopoverTop(hit.bottom + GAP_TB, viewport.height)
      left = Math.max(VIEWPORT_PAD, Math.min(hit.left - POPOVER_W, viewport.width - POPOVER_W - VIEWPORT_PAD))
    }
  }

  return clampPopoverInViewport({ top, left }, { width: POPOVER_W, height: POPOVER_H }, viewport)
}

function clampPopoverTop(top: number, viewportHeight: number): number {
  return clampPopoverInViewport(
    { top, left: VIEWPORT_PAD },
    { width: POPOVER_W, height: POPOVER_H },
    { width: POPOVER_W + VIEWPORT_PAD * 2, height: viewportHeight },
  ).top
}

export function rectFullyInViewport(
  rect: { top: number; left: number; width: number; height: number },
  viewport: { width: number; height: number },
  pad = VIEWPORT_PAD,
): boolean {
  return (
    rect.top >= pad &&
    rect.left >= pad &&
    rect.top + rect.height <= viewport.height - pad &&
    rect.left + rect.width <= viewport.width - pad
  )
}

/** Скролл якоря; если после auto/end низ всё ещё за краем — повтор с block:end. */
export function scrollTourAnchorIntoView(
  el: Element,
  options: { block: ScrollLogicalPosition; smooth: boolean },
): void {
  el.scrollIntoView({
    block: options.block,
    inline: 'nearest',
    behavior: options.smooth ? 'smooth' : 'auto',
  })
  if (typeof window === 'undefined') return
  const rect = el.getBoundingClientRect()
  if (rectFullyInViewport(rect, { width: window.innerWidth, height: window.innerHeight })) {
    return
  }
  el.scrollIntoView({ block: 'end', inline: 'nearest', behavior: 'auto' })
}
