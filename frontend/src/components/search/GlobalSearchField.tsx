import { useCallback, useEffect, useId, useRef, useState } from 'react'
import { useClickOutside } from '../../hooks/useClickOutside'
import { useQuery } from '@tanstack/react-query'
import { Link, useLocation, useNavigate } from 'react-router'
import { searchPortal, searchPortalSemantic } from '../../api/search/searchApi'
import {
  GLOBAL_SEARCH_PREVIEW_LIMIT,
  PORTAL_SEARCH_MIN_QUERY_LEN,
  PORTAL_SEARCH_MODE_LABELS,
  SEARCH_PAGE_ENTITY_TYPES,
  SEMANTIC_SEARCH_ENTITY_TYPES,
} from '../../constants/search'
import type { PortalSearchMode, SearchResult } from '../../types/search'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { isSemanticUnavailableError, parseSearchMode } from '@/utils/search/semanticSearchError'
import { getSearchResultHref } from '@/utils/search/searchNavigation'
import { portalSearchHeaderQueryKey } from '@/pages/search/searchQueryKeys'
import { SearchHitRow } from './SearchHitRow'
import layoutStyles from '@/styles/modules/layout/AppLayout.module.css'
import narrowStyles from '@/styles/modules/layout/AppLayoutNarrow.module.css'
import modeStyles from '@/styles/modules/search/SearchModeToggle.module.css'
import styles from '@/styles/modules/search/GlobalSearchField.module.css'

function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const t = window.setTimeout(() => setDebounced(value), delayMs)
    return () => window.clearTimeout(t)
  }, [value, delayMs])
  return debounced
}

function parseModeFromLocation(pathname: string, params: URLSearchParams): PortalSearchMode {
  if (pathname !== '/search') return 'fulltext'
  return parseSearchMode(params.get('mode'))
}

export function GlobalSearchField() {
  const navigate = useNavigate()
  const location = useLocation()
  const [searchInput, setSearchInput] = useState('')
  const [searchMode, setSearchMode] = useState<PortalSearchMode>(() =>
    parseModeFromLocation(location.pathname, new URLSearchParams(location.search)),
  )
  const debounced = useDebouncedValue(searchInput.trim(), 320)
  const [panelOpen, setPanelOpen] = useState(false)
  const [highlightedIndex, setHighlightedIndex] = useState(-1)
  const containerRef = useRef<HTMLDivElement>(null)
  const listboxId = useId()
  const optionRefs = useRef<Array<HTMLDivElement | null>>([])

  useEffect(() => {
    const params = new URLSearchParams(location.search)
    const qParam = params.get('q')
    if (location.pathname === '/search' && qParam !== null) {
      const t = window.setTimeout(() => {
        setSearchInput(qParam)
        setSearchMode(parseModeFromLocation(location.pathname, params))
      }, 0)
      return () => window.clearTimeout(t)
    }
    return undefined
  }, [location.pathname, location.search])

  const fulltextQuery = useQuery({
    queryKey: portalSearchHeaderQueryKey('fulltext', debounced, GLOBAL_SEARCH_PREVIEW_LIMIT),
    queryFn: () =>
      searchPortal({
        q: debounced,
        types: SEARCH_PAGE_ENTITY_TYPES,
        limit: GLOBAL_SEARCH_PREVIEW_LIMIT,
      }),
    enabled: searchMode === 'fulltext' && debounced.length >= PORTAL_SEARCH_MIN_QUERY_LEN,
    staleTime: 20_000,
  })

  const semanticQuery = useQuery({
    queryKey: portalSearchHeaderQueryKey('semantic', debounced, GLOBAL_SEARCH_PREVIEW_LIMIT),
    queryFn: () =>
      searchPortalSemantic({
        q: debounced,
        types: SEMANTIC_SEARCH_ENTITY_TYPES,
        limit: GLOBAL_SEARCH_PREVIEW_LIMIT,
      }),
    enabled: searchMode === 'semantic' && debounced.length >= PORTAL_SEARCH_MIN_QUERY_LEN,
    staleTime: 20_000,
    retry: (failureCount, err) => !isSemanticUnavailableError(err) && failureCount < 1,
  })

  const activeQuery = searchMode === 'semantic' ? semanticQuery : fulltextQuery
  const { isPending, isError, error } = activeQuery
  const results: SearchResult[] =
    searchMode === 'semantic'
      ? (semanticQuery.data?.results ?? [])
      : (fulltextQuery.data ?? [])
  const semanticUnavailable =
    searchMode === 'semantic' && isError && isSemanticUnavailableError(error)

  useEffect(() => {
    const t = window.setTimeout(() => setHighlightedIndex(-1), 0)
    return () => window.clearTimeout(t)
  }, [debounced, searchMode])

  // Скроллить клавиатурно-активную опцию в зону видимости (a11y combobox).
  useEffect(() => {
    if (highlightedIndex < 0) return
    const el = optionRefs.current[highlightedIndex]
    el?.scrollIntoView({ block: 'nearest' })
  }, [highlightedIndex])

  useClickOutside(panelOpen, [containerRef], () => setPanelOpen(false), 'mousedown')

  const trimmedInput = searchInput.trim()
  const maxHighlight = results.length - 1
  const showDropdown = panelOpen && trimmedInput.length > 0
  const waitingDebounce =
    trimmedInput.length >= PORTAL_SEARCH_MIN_QUERY_LEN &&
    debounced !== trimmedInput

  const goToResult = useCallback(
    (result: SearchResult) => {
      navigate(getSearchResultHref(result, { highlightQuery: trimmedInput }))
      setPanelOpen(false)
      setHighlightedIndex(-1)
    },
    [navigate, trimmedInput],
  )

  function buildSearchPageHref(q: string): string {
    const params = new URLSearchParams({ q })
    if (searchMode === 'semantic') params.set('mode', 'semantic')
    return `/search?${params}`
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const q = searchInput.trim()
    if (!q) return
    if (highlightedIndex >= 0 && results[highlightedIndex]) {
      goToResult(results[highlightedIndex])
      return
    }
    navigate(buildSearchPageHref(q))
    setPanelOpen(false)
  }

  function handleInputKeyDown(ev: React.KeyboardEvent<HTMLInputElement>) {
    if (ev.key === 'Escape') {
      setPanelOpen(false)
      return
    }
    if (ev.key === 'ArrowDown') {
      if (!panelOpen) {
        setPanelOpen(true)
      }
      if (trimmedInput.length < PORTAL_SEARCH_MIN_QUERY_LEN) return
      ev.preventDefault()
      setHighlightedIndex((i) => (maxHighlight < 0 ? -1 : Math.min(maxHighlight, i + 1)))
      return
    }
    if (!panelOpen) return
    if (trimmedInput.length < PORTAL_SEARCH_MIN_QUERY_LEN) return

    if (ev.key === 'ArrowUp') {
      ev.preventDefault()
      setHighlightedIndex((i) => Math.max(-1, i - 1))
    }
  }

  const showListBody =
    debounced.length >= PORTAL_SEARCH_MIN_QUERY_LEN &&
    !waitingDebounce &&
    !isPending &&
    !semanticUnavailable &&
    !isError &&
    results.length > 0

  return (
    <div ref={containerRef} className={`${styles.wrap} ${narrowStyles.searchWrap}`} data-tour="global-search">
      <form onSubmit={handleSubmit} className={`${layoutStyles.searchForm} ${narrowStyles.searchForm}`}>
        <div className={`${modeStyles.modeToggle} ${styles.modeToggle}`} role="group" aria-label="Режим поиска в шапке">
          {(['fulltext', 'semantic'] as const).map((m) => (
            <button
              key={m}
              type="button"
              className={`${modeStyles.modeBtn} ${styles.modeBtn} ${searchMode === m ? `${modeStyles.modeBtnActive} ${styles.modeBtnActive}` : ''}`}
              aria-pressed={searchMode === m}
              onClick={() => setSearchMode(m)}
            >
              {PORTAL_SEARCH_MODE_LABELS[m]}
            </button>
          ))}
        </div>
        <input
          type="search"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          onFocus={() => setPanelOpen(true)}
          onKeyDown={handleInputKeyDown}
          placeholder={
            searchMode === 'semantic' ? 'Поиск по смыслу…' : 'Поиск по порталу…'
          }
          aria-label="Поиск по порталу"
          className={`${layoutStyles.searchInput} ${narrowStyles.searchInput}`}
          autoComplete="off"
          role="combobox"
          aria-expanded={showDropdown}
          aria-haspopup="listbox"
          aria-autocomplete="list"
          aria-controls={listboxId}
          aria-activedescendant={
            highlightedIndex >= 0 && results[highlightedIndex]
              ? `${listboxId}-opt-${highlightedIndex}`
              : undefined
          }
        />
        <button type="submit" className={`${layoutStyles.searchBtn} ${narrowStyles.searchSubmit}`}>
          Найти
        </button>
      </form>

      {showDropdown ? (
        <div className={styles.dropdown} id={listboxId} role="listbox" aria-label="Результаты поиска">
          {trimmedInput.length < PORTAL_SEARCH_MIN_QUERY_LEN ? (
            <p className={styles.dropdownHint}>Введите не менее {PORTAL_SEARCH_MIN_QUERY_LEN} символов</p>
          ) : waitingDebounce || (debounced.length >= PORTAL_SEARCH_MIN_QUERY_LEN && isPending) ? (
            <p className={styles.dropdownHint}>Поиск…</p>
          ) : semanticUnavailable ? (
            <p className={styles.dropdownHint}>
              Семантический поиск недоступен. Переключитесь на «По тексту» или откройте страницу поиска.
            </p>
          ) : debounced.length >= PORTAL_SEARCH_MIN_QUERY_LEN && isError ? (
            <p className={styles.dropdownError} role="alert">
              {userFacingMessageFromUnknown(error)}
            </p>
          ) : debounced.length >= PORTAL_SEARCH_MIN_QUERY_LEN && results.length === 0 ? (
            <p className={styles.dropdownHint}>Ничего не найдено</p>
          ) : showListBody ? (
            <ul className={styles.resultList}>
              {results.map((result, index) => (
                <li key={`${result.entity_type}-${result.entity_id}`} className={styles.resultLi}>
                  <div
                    ref={(el) => {
                      optionRefs.current[index] = el
                    }}
                    id={`${listboxId}-opt-${index}`}
                    role="option"
                    aria-selected={highlightedIndex === index}
                    data-active={highlightedIndex === index ? '' : undefined}
                    onMouseEnter={() => setHighlightedIndex(index)}
                    onMouseDown={(e) => {
                      e.preventDefault()
                      goToResult(result)
                    }}
                  >
                    <SearchHitRow
                      result={result}
                      highlighted={highlightedIndex === index}
                      disableLinks
                      highlightQuery={trimmedInput}
                    />
                  </div>
                </li>
              ))}
            </ul>
          ) : null}
          {trimmedInput.length >= PORTAL_SEARCH_MIN_QUERY_LEN && !waitingDebounce && !isPending ? (
            <div className={styles.dropdownFooter}>
              <Link
                to={buildSearchPageHref(trimmedInput)}
                className={styles.allResultsLink}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => setPanelOpen(false)}
              >
                Все результаты
              </Link>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
