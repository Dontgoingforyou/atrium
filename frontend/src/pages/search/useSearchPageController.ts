import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router'
import { listTags } from '@/api/tags/tagsApi'
import { searchPortal, searchPortalSemantic } from '@/api/search/searchApi'
import { PORTAL_TAGS_QUERY_KEY } from '@/api/queryKeys'
import {
  PORTAL_SEARCH_MIN_QUERY_LEN,
  SEARCH_PAGE_ENTITY_TYPES,
  SEMANTIC_SEARCH_ENTITY_TYPES,
  SEMANTIC_SEARCH_PAGE_SIZE,
} from '@/constants/search'
import { userFacingMessageFromUnknown } from '@/utils/apiUserMessage'
import { isSemanticUnavailableError, parseSearchMode } from '@/utils/search/semanticSearchError'
import type { PortalSearchMode, SearchEntityType, SearchResult } from '@/types/search'
import { portalSearchPageQueryKey } from './searchQueryKeys'
import { parseTagSlugsFromSearchParams, setTagSlugsInSearchParams } from './searchPageUrl'
import { pruneActiveTypes, searchPageHasMore, visibleSearchEntityTypes } from './searchPageHelpers'

export type SearchPageController = ReturnType<typeof useSearchPageController>

export function useSearchPageController() {
  const [searchParams, setSearchParams] = useSearchParams()

  const q = searchParams.get('q') ?? ''
  const mode = parseSearchMode(searchParams.get('mode'))
  const tagSlugs = parseTagSlugsFromSearchParams(searchParams)

  const [input, setInput] = useState(q)
  const [activeTypes, setActiveTypes] = useState<SearchEntityType[]>([])
  const [page, setPage] = useState(0)
  const [prevQ, setPrevQ] = useState(q)
  const [prevMode, setPrevMode] = useState(mode)

  const filterTypes = useMemo(
    () =>
      visibleSearchEntityTypes(
        mode === 'semantic' ? SEMANTIC_SEARCH_ENTITY_TYPES : SEARCH_PAGE_ENTITY_TYPES,
      ),
    [mode],
  )

  if (prevQ !== q) {
    setPrevQ(q)
    setInput(q)
    setPage(0)
  }
  if (prevMode !== mode) {
    setPrevMode(mode)
    setPage(0)
    setActiveTypes((prev) => {
      const next = pruneActiveTypes(prev, filterTypes)
      if (next.length === prev.length && next.every((t, i) => t === prev[i])) return prev
      return next
    })
  }

  const visibleActiveTypes = pruneActiveTypes(activeTypes, filterTypes)
  const entityTypesForMode = visibleActiveTypes.length > 0 ? visibleActiveTypes : filterTypes

  const searchFilters = {
    tag_slugs: tagSlugs.length > 0 ? tagSlugs : undefined,
  }

  const {
    data: tags = [],
    isPending: tagsLoading,
    isError: tagsIsError,
    error: tagsError,
  } = useQuery({
    queryKey: PORTAL_TAGS_QUERY_KEY,
    queryFn: listTags,
  })

  const tagFilterOptions = useMemo(
    () => tags.map((t) => ({ value: t.slug, label: t.name })),
    [tags],
  )

  const tagsBySlug = useMemo(
    () => new Map(tags.map((t) => [t.slug, t])),
    [tags],
  )

  const fulltextQuery = useQuery({
    queryKey: portalSearchPageQueryKey('fulltext', q, visibleActiveTypes, page, tagSlugs),
    queryFn: () =>
      searchPortal({
        q,
        types: entityTypesForMode,
        ...searchFilters,
        skip: page * SEMANTIC_SEARCH_PAGE_SIZE,
        limit: SEMANTIC_SEARCH_PAGE_SIZE,
      }),
    enabled: mode === 'fulltext' && q.length >= PORTAL_SEARCH_MIN_QUERY_LEN,
  })

  const semanticQuery = useQuery({
    queryKey: portalSearchPageQueryKey('semantic', q, visibleActiveTypes, page, tagSlugs),
    queryFn: () =>
      searchPortalSemantic({
        q,
        types: entityTypesForMode,
        ...searchFilters,
        skip: page * SEMANTIC_SEARCH_PAGE_SIZE,
        limit: SEMANTIC_SEARCH_PAGE_SIZE,
      }),
    enabled: mode === 'semantic' && q.length >= PORTAL_SEARCH_MIN_QUERY_LEN,
    retry: (failureCount, err) => !isSemanticUnavailableError(err) && failureCount < 1,
  })

  const activeQuery = mode === 'semantic' ? semanticQuery : fulltextQuery
  const data: SearchResult[] | undefined =
    mode === 'semantic' ? semanticQuery.data?.results : fulltextQuery.data
  const { isPending, isError, error } = activeQuery
  const semanticUnavailable = mode === 'semantic' && isError && isSemanticUnavailableError(error)
  const semanticTotalFound = mode === 'semantic' ? semanticQuery.data?.total_found : undefined
  const skip = page * SEMANTIC_SEARCH_PAGE_SIZE
  const hasMore = searchPageHasMore({
    resultCount: data?.length ?? 0,
    pageSize: SEMANTIC_SEARCH_PAGE_SIZE,
    skip,
    totalFound: semanticTotalFound,
  })

  function applySearchParamsPatch(patch: (p: URLSearchParams) => URLSearchParams) {
    setPage(0)
    setSearchParams(patch(new URLSearchParams(searchParams)), { replace: true })
  }

  function setMode(next: PortalSearchMode) {
    applySearchParamsPatch((p) => {
      if (q) p.set('q', q)
      if (next === 'semantic') p.set('mode', 'semantic')
      else p.delete('mode')
      return p
    })
  }

  function submitSearch() {
    if (input.trim()) {
      applySearchParamsPatch((p) => {
        p.set('q', input.trim())
        if (mode === 'semantic') p.set('mode', 'semantic')
        else p.delete('mode')
        return p
      })
    }
  }

  function toggleType(t: SearchEntityType) {
    setPage(0)
    setActiveTypes((prev) => (prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]))
  }

  function setFilterTagSlugs(slugs: string[]) {
    applySearchParamsPatch((p) => setTagSlugsInSearchParams(p, slugs))
  }

  function resetExtraFilters() {
    applySearchParamsPatch((p) => {
      p.delete('tag_slug')
      return p
    })
  }

  return {
    q,
    mode,
    tagSlugs,
    input,
    setInput,
    activeTypes: visibleActiveTypes,
    page,
    setPage,
    tags,
    tagsLoading,
    tagsIsError,
    tagsErrorMessage: tagsIsError ? userFacingMessageFromUnknown(tagsError) : null,
    tagFilterOptions,
    tagsBySlug,
    data,
    isPending,
    isError,
    error,
    errorMessage: isError ? userFacingMessageFromUnknown(error) : null,
    semanticUnavailable,
    semanticTotalFound,
    filterTypes,
    hasMore,
    setMode,
    submitSearch,
    toggleType,
    setFilterTagSlugs,
    resetExtraFilters,
    clearActiveTypes: () => {
      setActiveTypes([])
      setPage(0)
    },
  }
}
