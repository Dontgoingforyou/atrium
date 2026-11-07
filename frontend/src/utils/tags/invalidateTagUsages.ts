import type { QueryClient } from '@tanstack/react-query'

import { TAG_USAGES_QUERY_KEY_PREFIX } from './tagUsagesQueryKeys'

/** Сброс кэша drawer «Связи тега» после изменения тегов у задач/документов. */
export function invalidateTagUsages(queryClient: QueryClient): void {
  void queryClient.invalidateQueries({ queryKey: TAG_USAGES_QUERY_KEY_PREFIX })
}
