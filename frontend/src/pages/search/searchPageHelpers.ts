import type { SearchEntityType } from '../../types/search'

/** Раздел «Обучение» заморожен в UI (`/learning` → `/`); не предлагать в фильтрах страницы поиска. */
const FROZEN_SEARCH_ENTITY_TYPES = new Set<SearchEntityType>(['learning_material'])

export const SEMANTIC_SEARCH_UNAVAILABLE_USER_MESSAGE =
  'Семантический поиск временно недоступен.'

export function visibleSearchEntityTypes(
  types: readonly SearchEntityType[],
): SearchEntityType[] {
  return types.filter((t) => !FROZEN_SEARCH_ENTITY_TYPES.has(t))
}

export function pruneActiveTypes(
  active: readonly SearchEntityType[],
  allowed: readonly SearchEntityType[],
): SearchEntityType[] {
  const allow = new Set(allowed)
  return active.filter((t) => allow.has(t))
}

export function searchPageHasMore(opts: {
  resultCount: number
  pageSize: number
  skip: number
  totalFound?: number
}): boolean {
  if (typeof opts.totalFound === 'number') {
    return opts.skip + opts.resultCount < opts.totalFound
  }
  return opts.resultCount >= opts.pageSize
}

export function searchResultsShownRange(opts: {
  skip: number
  resultCount: number
}): { from: number; to: number } {
  return { from: opts.skip + 1, to: opts.skip + opts.resultCount }
}
