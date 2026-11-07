import { Link } from 'react-router'
import { SEARCH_ENTITY_LABELS } from '../../constants/search'
import type { SearchResult } from '../../types/search'
import { formatSimilarityBadge } from '@/utils/search/formatSimilarityBadge'
import { getSearchResultHref } from '@/utils/search/searchNavigation'
import { HighlightedPlainText } from './HighlightedPlainText'
import styles from '@/styles/modules/search/SearchPage.module.css'

function displayTitle(result: SearchResult): string {
  return (
    result.title ??
    (result.entity_type === 'chat_message' ? result.message?.body?.slice(0, 80) : null) ??
    result.entity_id
  )
}

function shouldShowSnippet(result: SearchResult, title: string): boolean {
  if (!result.snippet) return false
  const snippet = result.snippet.trim()
  const titleTrimmed = title.trim()
  return snippet.length > 0 && snippet !== titleTrimmed
}

export type SearchHitRowProps = {
  result: SearchResult
  /** Подсветка строки (клавиатура в выпадающем списке) */
  highlighted?: boolean
  /** Без ссылок — родитель обрабатывает переход (выпадающий список в шапке) */
  disableLinks?: boolean
  /** Текущий поисковый запрос — уйдёт в `?highlight=` на целевой странице и подсветит совпадения */
  highlightQuery?: string | null
  /** Режим «по смыслу»: не красить предлоги и короткие служебные токены */
  dropServiceTokens?: boolean
}

export function SearchHitRow({
  result,
  highlighted,
  disableLinks,
  highlightQuery,
  dropServiceTokens,
}: SearchHitRowProps) {
  const href = getSearchResultHref(result, { highlightQuery })
  const title = displayTitle(result)
  const hasQuery = highlightQuery != null && highlightQuery.trim().length > 0
  const tokenizeOptions = dropServiceTokens ? { dropServiceTokens: true } : undefined

  const titleNode = disableLinks ? (
    <span className={styles.resultTitleLink}>
      {hasQuery ? (
        <HighlightedPlainText text={title} query={highlightQuery} tokenizeOptions={tokenizeOptions} />
      ) : (
        title
      )}
    </span>
  ) : (
    <Link to={href} className={styles.resultTitleLink}>
      {hasQuery ? (
        <HighlightedPlainText text={title} query={highlightQuery} tokenizeOptions={tokenizeOptions} />
      ) : (
        title
      )}
    </Link>
  )

  return (
    <div className={`${styles.resultCard} ${highlighted ? styles.resultCardHighlighted : ''}`}>
      <div className={styles.resultCardHeader}>
        <div className={styles.resultCardHeaderMain}>
          <span className={styles.resultTypeBadge}>
            {SEARCH_ENTITY_LABELS[result.entity_type] ?? result.entity_type}
          </span>
          {titleNode}
        </div>
        {result.similarity_score != null ? (
          <span className={styles.similarityBadge} title="Косинусная похожесть запроса и текста">
            {formatSimilarityBadge(result.similarity_score)}
          </span>
        ) : null}
      </div>
      {shouldShowSnippet(result, title) ? (
        <p className={styles.resultSnippet}>
          {hasQuery ? (
            <HighlightedPlainText
              text={result.snippet ?? ''}
              query={highlightQuery}
              tokenizeOptions={tokenizeOptions}
            />
          ) : (
            result.snippet
          )}
        </p>
      ) : null}
    </div>
  )
}
