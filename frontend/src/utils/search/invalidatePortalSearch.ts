import type { QueryClient } from '@tanstack/react-query'
import { PORTAL_SEARCH_QUERY_KEY_PREFIX } from '@/api/queryKeys'

/** Сбросить кэш глобального поиска (шапка и /search) после удаления сущностей из индекса. */
export function invalidatePortalSearchQueries(qc: QueryClient): void {
  void qc.invalidateQueries({ queryKey: [...PORTAL_SEARCH_QUERY_KEY_PREFIX] })
}
