import {
  highlightExactPlainTextParts,
  highlightPlainTextParts,
  type TokenizeHighlightOptions,
} from '../../utils/search/searchHighlight'
import { isSafeExternalUrl } from '../../utils/safeExternalUrl'
import { splitTextWithSafeUrls } from '../tasks/taskCommentsMentionRender'
import hitStyles from '@/styles/modules/search/SearchHitMark.module.css'
import styles from '@/styles/modules/ui/LinkifiedPlainText.module.css'

type Props = {
  text: string
  query: string | null | undefined
  /** Непрерывный фрагмент (цитата), а не токены поиска. */
  matchExact?: boolean
  tokenizeOptions?: TokenizeHighlightOptions
}

function HighlightedSpan({
  text,
  query,
  matchExact = false,
  tokenizeOptions,
}: {
  text: string
  query: string | null | undefined
  matchExact?: boolean
  tokenizeOptions?: TokenizeHighlightOptions
}) {
  if (!query) return <>{text}</>
  const parts = matchExact
    ? highlightExactPlainTextParts(text, query)
    : highlightPlainTextParts(text, query, tokenizeOptions)
  return (
    <>
      {parts.map((part, i) =>
        part.type === 'mark' ? (
          <mark
            key={i}
            className={matchExact ? hitStyles.hitExact : hitStyles.hit}
            data-search-hit={matchExact ? 'exact' : '1'}
          >
            {part.value}
          </mark>
        ) : (
          <span key={i}>{part.value}</span>
        ),
      )}
    </>
  )
}

/** Plain text с подсветкой поиска и кликабельными http(s)-ссылками. */
export function HighlightedPlainText({
  text,
  query,
  matchExact = false,
  tokenizeOptions,
}: Props) {
  const segments = splitTextWithSafeUrls(text)
  return (
    <>
      {segments.map((seg, i) => {
        if (seg.type === 'link' && isSafeExternalUrl(seg.value)) {
          return (
            <a
              key={i}
              href={seg.value}
              target="_blank"
              rel="noopener noreferrer"
              className={styles.externalLink}
              onClick={(e) => e.stopPropagation()}
            >
              {seg.value}
            </a>
          )
        }
        return (
          <span key={i}>
            <HighlightedSpan
              text={seg.value}
              query={query}
              matchExact={matchExact}
              tokenizeOptions={tokenizeOptions}
            />
          </span>
        )
      })}
    </>
  )
}
