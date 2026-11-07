import type {
  SearchParams,
  SearchResult,
  SemanticSearchParams,
  SemanticSearchResponse,
} from '../../types/search'
import { normalizePortalSearchResults } from '@/utils/search/normalizeSearchHit'
import { normalizePortalSemanticResults } from '@/utils/search/normalizeSemanticHit'
import { parseJsonOrThrowApi } from '../parseResponse'
import { authenticatedFetch } from '../rawClient'

/** Общая сборка query string для обоих эндпоинтов поиска. */
function buildSearchQuery(params: SearchParams): URLSearchParams {
  const qs = new URLSearchParams()
  qs.set('q', params.q)
  if (params.types && params.types.length > 0) {
    params.types.forEach((t) => qs.append('types', t))
  }
  if (params.tag_slugs?.length) {
    params.tag_slugs.forEach((slug) => qs.append('tag_slug', slug))
  }
  if (params.status_ids?.length) {
    params.status_ids.forEach((id) => qs.append('status_ids', id))
  }
  if (params.skip !== undefined) qs.set('skip', String(params.skip))
  if (params.limit !== undefined) qs.set('limit', String(params.limit))
  return qs
}

export async function searchPortal(params: SearchParams): Promise<SearchResult[]> {
  const qs = buildSearchQuery(params)
  const res = await authenticatedFetch(`/portal/search?${qs}`)
  const raw = await parseJsonOrThrowApi(res)
  return normalizePortalSearchResults(raw)
}

export async function searchPortalSemantic(
  params: SemanticSearchParams,
): Promise<SemanticSearchResponse> {
  const qs = buildSearchQuery(params)
  const res = await authenticatedFetch(`/portal/search/semantic?${qs}`)
  const raw = await parseJsonOrThrowApi(res)
  const root = raw as { query?: string; total_found?: number }
  return {
    query: typeof root.query === 'string' ? root.query : params.q,
    total_found: typeof root.total_found === 'number' ? root.total_found : 0,
    results: normalizePortalSemanticResults(raw),
  }
}
