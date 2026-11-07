import { PORTAL_TAGS_QUERY_KEY } from '@/api/queryKeys'
import { TAG_USAGES_QUERY_KEY_PREFIX } from '@/utils/tags/tagUsagesQueryKeys'

export { TAG_USAGES_QUERY_KEY_PREFIX }

export function tagUsagesQueryKey(tagId: string) {
  return [...TAG_USAGES_QUERY_KEY_PREFIX, tagId] as const
}

export { PORTAL_TAGS_QUERY_KEY }
