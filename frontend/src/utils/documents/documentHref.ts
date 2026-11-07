import type { SearchResult } from '../../types/search'
import { getSearchResultHref } from '../search/searchNavigation'

export function getDocumentPublicHref(documentId: string, navNodeSlug?: string | null): string {
  const stub: Pick<SearchResult, 'entity_type' | 'entity_id' | 'nav_node_slug'> = {
    entity_type: 'document',
    entity_id: documentId,
    nav_node_slug: navNodeSlug ?? null,
  }
  return getSearchResultHref(stub as SearchResult)
}

export function getDocumentPublicUrl(documentId: string, navNodeSlug?: string | null): string {
  return `${window.location.origin}${getDocumentPublicHref(documentId, navNodeSlug)}`
}
