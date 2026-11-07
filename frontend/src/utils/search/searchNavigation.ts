import type { SearchResult } from '../../types/search'
import {
  SEARCH_HIGHLIGHT_PARAM,
  clampHighlightQuery,
} from './searchHighlight'

export type SearchResultHrefOptions = {
  highlightQuery?: string | null
}

function withHighlight(path: string, highlightQuery?: string | null): string {
  const q = clampHighlightQuery(highlightQuery)
  if (!q) return path
  const [base, existingQs] = path.split('?', 2)
  const params = new URLSearchParams(existingQs ?? '')
  params.set(SEARCH_HIGHLIGHT_PARAM, q)
  const qs = params.toString()
  return qs ? `${base}?${qs}` : base
}

export function getSearchResultHref(
  result: SearchResult,
  options?: SearchResultHrefOptions,
): string {
  const highlightQuery = options?.highlightQuery
  switch (result.entity_type) {
    case 'document': {
      const path =
        result.nav_node_slug != null && result.nav_node_slug !== ''
          ? `/p/${encodeURIComponent(result.nav_node_slug)}/documents/${encodeURIComponent(result.entity_id)}`
          : `/documents/${encodeURIComponent(result.entity_id)}`
      return withHighlight(path, highlightQuery)
    }
    case 'chat_message': {
      const chatId = result.chat?.id
      if (!chatId) return withHighlight('/chats', highlightQuery)
      const messageId = result.message?.id ?? result.entity_id
      const qs = new URLSearchParams()
      qs.set('chat', chatId)
      if (messageId) qs.set('message', messageId)
      const q = clampHighlightQuery(highlightQuery)
      if (q) qs.set(SEARCH_HIGHLIGHT_PARAM, q)
      return `/chats?${qs.toString()}`
    }
    case 'task':
      return withHighlight(`/tasks/${encodeURIComponent(result.entity_id)}`, highlightQuery)
    case 'specialist':
      return withHighlight(
        `/specialists?sub=${encodeURIComponent(result.entity_id)}`,
        highlightQuery,
      )
    case 'learning_material':
      // Раздел «Обучение» временно заморожен в UI
      return '/'
    case 'specialist_note':
      if (result.specialist_sub) {
        return withHighlight(
          `/specialists?sub=${encodeURIComponent(result.specialist_sub)}`,
          highlightQuery,
        )
      }
      return withHighlight('/specialists', highlightQuery)
    case 'calendar_event':
      return withHighlight(
        `/calendar?event=${encodeURIComponent(result.entity_id)}`,
        highlightQuery,
      )
    default:
      return '/'
  }
}
