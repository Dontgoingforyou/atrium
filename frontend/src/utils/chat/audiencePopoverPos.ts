import type { CSSProperties } from 'react'

export type AudienceAnchorRect = {
  top: number
  bottom: number
  left: number
  right: number
}

export function audiencePopoverStyle(
  anchorRect: AudienceAnchorRect,
  popoverW: number,
): CSSProperties {
  const gap = 6
  const margin = 8
  const vw = window.innerWidth
  const vh = window.innerHeight
  const width = Math.min(popoverW, vw - margin * 2)
  const { top, bottom, right } = anchorRect
  const showAbove = bottom > vh / 2 && top - gap > margin
  const posTop = showAbove ? top - gap : bottom + gap
  const transform = showAbove ? 'translateY(-100%)' : undefined
  const posLeft = Math.max(margin, Math.min(right, vw - margin) - width)
  return { left: posLeft, top: posTop, transform, width }
}
