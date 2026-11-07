import { useEffect, useRef, type RefObject } from 'react'

import { SEARCH_HIGHLIGHT_ATTR } from '../utils/search/searchHighlight'

const HIT_SELECTOR = `mark[${SEARCH_HIGHLIGHT_ATTR}="1"]`

export function useScrollToSearchHit(
  containerRef: RefObject<HTMLElement | null>,
  highlightQuery: string | null,
  ready: boolean = true,
): void {
  const scrolledForQueryRef = useRef<string | null>(null)

  useEffect(() => {
    if (!highlightQuery || !ready) return
    if (scrolledForQueryRef.current === highlightQuery) return

    const root = containerRef.current
    if (!root) return

    const first = root.querySelector(HIT_SELECTOR)
    if (!first) return

    scrolledForQueryRef.current = highlightQuery
    first.scrollIntoView({ block: 'center', behavior: 'smooth' })
  }, [containerRef, highlightQuery, ready])
}
