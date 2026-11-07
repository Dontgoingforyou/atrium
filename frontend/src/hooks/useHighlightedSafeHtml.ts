import { useMemo } from 'react'

import { highlightInSanitizedHtml } from '../utils/search/searchHighlight'

export function useHighlightedSafeHtml(
  safeHtml: string,
  highlightQuery: string | null | undefined,
): string {
  return useMemo(() => {
    if (!highlightQuery || !safeHtml) return safeHtml
    return highlightInSanitizedHtml(safeHtml, highlightQuery)
  }, [safeHtml, highlightQuery])
}
