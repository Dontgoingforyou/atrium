import { useMemo } from 'react'
import { useSearchParams } from 'react-router'

import {
  SEARCH_HIGHLIGHT_PARAM,
  clampHighlightQuery,
} from '../utils/search/searchHighlight'

/** Читает `?highlight=` из URL (уже clamp). */
export function useSearchHighlightQuery(): string | null {
  const [searchParams] = useSearchParams()
  return useMemo(
    () => clampHighlightQuery(searchParams.get(SEARCH_HIGHLIGHT_PARAM)),
    [searchParams],
  )
}
