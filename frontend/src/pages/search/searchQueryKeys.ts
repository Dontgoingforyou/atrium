import { PORTAL_SEARCH_QUERY_KEY_PREFIX } from '@/api/queryKeys'
import type { PortalSearchMode, SearchEntityType } from '@/types/search'

export function portalSearchHeaderQueryKey(
  mode: PortalSearchMode,
  q: string,
  limit: number,
): readonly unknown[] {
  return [...PORTAL_SEARCH_QUERY_KEY_PREFIX, 'header', mode, q, limit]
}

export function portalSearchPageQueryKey(
  mode: PortalSearchMode,
  q: string,
  activeTypes: SearchEntityType[],
  page: number,
  tagSlugs: string[],
): readonly unknown[] {
  return [...PORTAL_SEARCH_QUERY_KEY_PREFIX, 'page', mode, q, activeTypes, page, tagSlugs]
}
