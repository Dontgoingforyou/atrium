import { SearchableMultiPicker } from '../components/common/SearchableMultiPicker'
import { TagChip } from '../components/tags/TagChip'
import { SearchHitRow } from '../components/search/SearchHitRow'
import {
  PORTAL_SEARCH_MIN_QUERY_LEN,
  PORTAL_SEARCH_MODE_LABELS,
  SEMANTIC_SEARCH_PAGE_SIZE,
  SEARCH_ENTITY_LABELS,
} from '../constants/search'
import type { PortalSearchMode } from '../types/search'
import { useSearchPageController } from './search/useSearchPageController'
import {
  SEMANTIC_SEARCH_UNAVAILABLE_USER_MESSAGE,
  searchResultsShownRange,
} from './search/searchPageHelpers'
import modeStyles from '@/styles/modules/search/SearchModeToggle.module.css'
import styles from '@/styles/modules/search/SearchPage.module.css'

const SEARCH_MODES: readonly PortalSearchMode[] = ['fulltext', 'semantic']

export function SearchPage() {
  const c = useSearchPageController()
  const {
    q,
    mode,
    tagSlugs,
    input,
    setInput,
    activeTypes,
    page,
    setPage,
    tagsLoading,
    tagsIsError,
    tagsErrorMessage,
    tagFilterOptions,
    tagsBySlug,
    data,
    isPending,
    isError,
    errorMessage,
    semanticUnavailable,
    semanticTotalFound,
    filterTypes,
    hasMore,
    setMode,
    submitSearch,
    toggleType,
    setFilterTagSlugs,
    resetExtraFilters,
    clearActiveTypes,
  } = c

  function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    submitSearch()
  }

  function handleModeKeyDown(e: React.KeyboardEvent<HTMLDivElement>) {
    const idx = SEARCH_MODES.indexOf(mode)
    if (idx < 0) return
    if (e.key === 'ArrowRight') {
      e.preventDefault()
      setMode(SEARCH_MODES[(idx + 1) % SEARCH_MODES.length])
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault()
      setMode(SEARCH_MODES[(idx - 1 + SEARCH_MODES.length) % SEARCH_MODES.length])
    } else if (e.key === 'Home') {
      e.preventDefault()
      setMode(SEARCH_MODES[0])
    } else if (e.key === 'End') {
      e.preventDefault()
      setMode(SEARCH_MODES[SEARCH_MODES.length - 1])
    }
  }

  const shownRange =
    data && data.length > 0
      ? searchResultsShownRange({
          skip: page * SEMANTIC_SEARCH_PAGE_SIZE,
          resultCount: data.length,
        })
      : null

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Поиск</h1>
      </div>

      <div
        className={`${modeStyles.modeToggle} ${styles.modeToggle}`}
        role="group"
        aria-label="Режим поиска"
        data-tour="search-mode"
        onKeyDown={handleModeKeyDown}
      >
        {SEARCH_MODES.map((m) => (
          <button
            key={m}
            type="button"
            aria-pressed={mode === m}
            className={`${modeStyles.modeBtn} ${styles.modeBtn} ${
              mode === m ? `${modeStyles.modeBtnActive} ${styles.modeBtnActive}` : ''
            }`}
            onClick={() => setMode(m)}
          >
            {PORTAL_SEARCH_MODE_LABELS[m]}
          </button>
        ))}
      </div>

      <form onSubmit={handleSearch} className="filter-bar">
        <input
          type="search"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={mode === 'semantic' ? 'Опишите, что ищете…' : 'Введите запрос…'}
          aria-label="Поиск по порталу"
          autoFocus
          className={styles.searchInput}
        />
        <button type="submit" className={styles.searchSubmitBtn}>
          Найти
        </button>
      </form>

      {mode === 'semantic' ? (
        <p className={`text-caption ${styles.semanticHint}`}>
          Поиск по смыслу через эмбеддинги. Запрос отправляется провайдеру OpenAI. Для точных фрагментов слов
          используйте режим «По тексту».
        </p>
      ) : null}

      <div className={styles.tagFilterSection}>
        <div className={styles.tagFilterRow}>
          <span className={styles.tagFilterLabel}>Теги документов:</span>
          <div className={styles.tagFilterPicker}>
            <SearchableMultiPicker
              value={tagSlugs}
              onChange={setFilterTagSlugs}
              options={tagFilterOptions}
              placeholder="Все — начните вводить тег…"
              loading={tagsLoading}
              hideChips
              chipsAriaLabel="Выбранные теги"
            />
          </div>
        </div>

        {tagsIsError ? <p className="text-danger">{tagsErrorMessage}</p> : null}

        {tagSlugs.length > 0 ? (
          <div className={styles.tagChipsRow}>
            {tagSlugs.map((slug) => {
              const tag = tagsBySlug.get(slug)
              return (
                <TagChip key={slug} storedColor={tag?.color ?? ''} className={styles.tagChip}>
                  <span className={styles.tagChipLabel}>{tag?.name ?? slug}</span>
                  <button
                    type="button"
                    className={styles.tagChipRemove}
                    title="Убрать тег"
                    aria-label={tag ? 'Убрать тег' : `Убрать тег ${slug}`}
                    onClick={() => setFilterTagSlugs(tagSlugs.filter((s) => s !== slug))}
                  >
                    ×
                  </button>
                </TagChip>
              )
            })}
            <button type="button" className={styles.resetFiltersBtn} onClick={resetExtraFilters}>
              Сбросить теги
            </button>
          </div>
        ) : null}
      </div>

      <div className={styles.typeFilters}>
        {filterTypes.map((t) => (
          <button
            key={t}
            type="button"
            aria-pressed={activeTypes.includes(t)}
            onClick={() => toggleType(t)}
            className={`${styles.typeBtn} ${activeTypes.includes(t) ? styles.typeBtnActive : ''}`}
          >
            {SEARCH_ENTITY_LABELS[t]}
          </button>
        ))}
        {activeTypes.length > 0 ? (
          <button type="button" onClick={clearActiveTypes} className={styles.resetFiltersBtn}>
            Сбросить типы
          </button>
        ) : null}
      </div>

      {!q ? null : q.length < PORTAL_SEARCH_MIN_QUERY_LEN ? (
        <p className="text-muted">Введите не менее {PORTAL_SEARCH_MIN_QUERY_LEN} символов</p>
      ) : semanticUnavailable ? (
        <p className="text-muted">{SEMANTIC_SEARCH_UNAVAILABLE_USER_MESSAGE}</p>
      ) : isPending ? (
        <p className="text-muted">Поиск…</p>
      ) : isError ? (
        <p className="text-danger">{errorMessage}</p>
      ) : !data || data.length === 0 ? (
        <p className="text-muted">
          {page > 0 ? 'Больше результатов нет.' : `Ничего не найдено по запросу «${q}»`}
        </p>
      ) : (
        <div className={styles.results}>
          <p className={`text-caption ${styles.resultsCount}`}>
            Показано: {shownRange?.from}–{shownRange?.to}
            {typeof semanticTotalFound === 'number' ? ` из ${semanticTotalFound}` : ''}
            {mode === 'semantic' ? ' · по релевантности' : ''}
          </p>
          {data.map((result) => (
            <SearchHitRow
              key={`${result.entity_type}-${result.entity_id}`}
              result={result}
              highlightQuery={q}
              dropServiceTokens={mode === 'semantic'}
            />
          ))}
          <div className={styles.paginationRow}>
            {page > 0 ? (
              <button type="button" className="btn-secondary" onClick={() => setPage((p) => p - 1)}>
                Назад
              </button>
            ) : null}
            {hasMore ? (
              <button type="button" className="btn-secondary" onClick={() => setPage((p) => p + 1)}>
                Вперёд
              </button>
            ) : null}
          </div>
        </div>
      )}
    </div>
  )
}
