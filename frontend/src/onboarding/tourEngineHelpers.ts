import { canonicalTourPathname } from '../domain/onboarding/guidedTourPages'
import {
  pickPopoverPlacement,
  popoverPosition,
  type PopoverPlacement,
} from '../utils/guidedTourLayout'
import type { SpotlightRect } from './TourSpotlight'

export type TargetRect = SpotlightRect & { bottom: number; right: number }

export const POPOVER_FADE_MS = 80
export const AFTER_SCROLL_MS = 50

export function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined') return true
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

export function readRect(el: Element): TargetRect {
  const r = el.getBoundingClientRect()
  return {
    top: r.top,
    left: r.left,
    width: r.width,
    height: r.height,
    bottom: r.bottom,
    right: r.right,
  }
}

export function routeMatches(currentPath: string, currentSearch: string, stepRoute: string | undefined): boolean {
  if (!stepRoute) return true
  const [path, query = ''] = stepRoute.split('?')
  if (canonicalTourPathname(currentPath) !== canonicalTourPathname(path)) return false
  if (!query) return true
  const want = new URLSearchParams(query)
  const have = new URLSearchParams(currentSearch.startsWith('?') ? currentSearch.slice(1) : currentSearch)
  for (const [k, v] of want.entries()) {
    if (have.get(k) !== v) return false
  }
  return true
}

export function resolveTourOpenHref(el: Element): string | null {
  if (el instanceof HTMLAnchorElement) {
    const href = el.getAttribute('href')
    if (href && isTourInternalPath(href)) return href
  }
  const custom = el.getAttribute('data-tour-route')
  if (custom && isTourInternalPath(custom)) return custom
  return null
}

function isTourInternalPath(href: string): boolean {
  const trimmed = href.trim()
  if (!trimmed.startsWith('/') || trimmed.startsWith('//')) return false
  if (trimmed.includes('\\')) return false
  return true
}

export function locationMatchesHref(pathname: string, search: string, href: string): boolean {
  const [path, query = ''] = href.split('?')
  if (canonicalTourPathname(pathname) !== canonicalTourPathname(path)) return false
  if (!query) return true
  const want = new URLSearchParams(query)
  const have = new URLSearchParams(search.startsWith('?') ? search.slice(1) : search)
  for (const [k, v] of want.entries()) {
    if (have.get(k) !== v) return false
  }
  return true
}

export function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms))
}

export function computePopoverPos(
  rect: SpotlightRect | null,
  prefer?: PopoverPlacement,
): { top: number; left: number } {
  if (!rect || typeof window === 'undefined') return { top: 24, left: 24 }
  const viewport = { width: window.innerWidth, height: window.innerHeight }
  const full = {
    ...rect,
    bottom: rect.top + rect.height,
    right: rect.left + rect.width,
  }
  return popoverPosition(full, pickPopoverPlacement(full, viewport, prefer), viewport)
}

const TOUR_REVEAL_ATTR = 'data-tour-reveal'

export function clearTourReveal(): void {
  document.querySelectorAll(`[${TOUR_REVEAL_ATTR}]`).forEach((node) => {
    node.removeAttribute(TOUR_REVEAL_ATTR)
  })
}

export function applyTourReveal(el: Element): void {
  clearTourReveal()
  el.setAttribute(TOUR_REVEAL_ATTR, '1')
}
