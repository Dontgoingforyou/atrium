import { htmlHasEmbeddedRichMedia } from './isEmptyHtml'

const HTML_TAG_RE = /<[^>]+>/g

/** Plain-text excerpt из HTML без сетевых запросов (канбан, списки). */
export function htmlToPlainTextExcerpt(html: string | null | undefined, maxLen = 140): string {
  if (!html?.trim()) return ''
  const text = html.replace(HTML_TAG_RE, ' ').replace(/\s+/g, ' ').trim()
  if (text.length > 0) {
    if (text.length <= maxLen) return text
    return `${text.slice(0, maxLen).trimEnd()}…`
  }
  if (htmlHasEmbeddedRichMedia(html)) {
    return 'Изображение'
  }
  return ''
}
