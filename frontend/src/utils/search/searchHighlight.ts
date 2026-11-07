/** Query-параметр URL с поисковой строкой для подсветки на целевой странице. */
export const SEARCH_HIGHLIGHT_PARAM = 'highlight'

/** Атрибут на `<mark>` — для стилей и scrollIntoView. */
export const SEARCH_HIGHLIGHT_ATTR = 'data-search-hit'

export const SEARCH_HIGHLIGHT_QUERY_MAX_LEN = 100

const MIN_TOKEN_LEN_DEFAULT = 2
const MIN_TOKEN_LEN_SEMANTIC = 3

/** Только режим «по смыслу»: иначе «найти … на бенч» красит каждый предлог «на». */
const HIGHLIGHT_STOPWORDS = new Set([
  'на',
  'по',
  'для',
  'от',
  'из',
  'до',
  'за',
  'не',
  'ни',
  'во',
  'со',
  'об',
  'при',
  'про',
  'без',
  'или',
  'как',
  'что',
  'это',
  'the',
  'and',
  'for',
])

export type TokenizeHighlightOptions = {
  /** Карточка семантической выдачи: стоп-слова и токены короче 3. */
  dropServiceTokens?: boolean
}

export type HighlightPlainPart = {
  type: 'text' | 'mark'
  value: string
}

/** Обрезает и нормализует строку для `?highlight=`; пустая → null. */
export function clampHighlightQuery(raw: string | null | undefined): string | null {
  if (raw == null) return null
  const trimmed = raw.trim()
  if (!trimmed) return null
  if (trimmed.length <= SEARCH_HIGHLIGHT_QUERY_MAX_LEN) return trimmed
  return trimmed.slice(0, SEARCH_HIGHLIGHT_QUERY_MAX_LEN)
}

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

/**
 * Токены для подсветки: слова ≥2 символов, без дубликатов по lower-case
 * (сохраняем первое написание). Стоп-слова — только при `dropServiceTokens`.
 */
export function tokenizeHighlightQuery(
  query: string,
  options?: TokenizeHighlightOptions,
): string[] {
  const minLen = options?.dropServiceTokens ? MIN_TOKEN_LEN_SEMANTIC : MIN_TOKEN_LEN_DEFAULT
  const parts = query
    .trim()
    .split(/\s+/)
    .map((t) => t.trim())
    .filter((t) => t.length >= minLen)
  const seen = new Set<string>()
  const out: string[] = []
  for (const t of parts) {
    const key = t.toLowerCase()
    if (seen.has(key)) continue
    if (options?.dropServiceTokens && HIGHLIGHT_STOPWORDS.has(key)) continue
    seen.add(key)
    out.push(t)
  }
  return out
}

function buildTokenRegex(tokens: readonly string[]): RegExp | null {
  if (tokens.length === 0) return null
  const alt = tokens.map(escapeRegExp).join('|')
  return new RegExp(`(${alt})`, 'gi')
}

/** Разбивает plain text на фрагменты text/mark для React-рендера. */
export function highlightPlainTextParts(
  text: string,
  query: string,
  options?: TokenizeHighlightOptions,
): HighlightPlainPart[] {
  const tokens = tokenizeHighlightQuery(query, options)
  const re = buildTokenRegex(tokens)
  if (!re || !text) return [{ type: 'text', value: text }]

  const parts: HighlightPlainPart[] = []
  let last = 0
  for (const match of text.matchAll(re)) {
    const idx = match.index ?? 0
    if (idx > last) {
      parts.push({ type: 'text', value: text.slice(last, idx) })
    }
    parts.push({ type: 'mark', value: match[0] })
    last = idx + match[0].length
  }
  if (last < text.length) {
    parts.push({ type: 'text', value: text.slice(last) })
  }
  return parts.length > 0 ? parts : [{ type: 'text', value: text }]
}

/**
 * Подсветка непрерывного фрагмента (цитата ответа в чате), без разбиения на слова.
 * Регистр не учитывается; берётся первое вхождение.
 */
export function highlightExactPlainTextParts(text: string, exact: string): HighlightPlainPart[] {
  const needle = exact.trim()
  if (!needle || !text) return [{ type: 'text', value: text }]
  const idx = text.toLowerCase().indexOf(needle.toLowerCase())
  if (idx < 0) return [{ type: 'text', value: text }]
  const end = idx + needle.length
  const parts: HighlightPlainPart[] = []
  if (idx > 0) parts.push({ type: 'text', value: text.slice(0, idx) })
  parts.push({ type: 'mark', value: text.slice(idx, end) })
  if (end < text.length) parts.push({ type: 'text', value: text.slice(end) })
  return parts
}

function wrapMatchesInTextNode(textNode: Text, re: RegExp, doc: Document): void {
  const text = textNode.nodeValue ?? ''
  if (!text) return
  re.lastIndex = 0
  const matches = [...text.matchAll(re)]
  if (matches.length === 0) return

  const frag = doc.createDocumentFragment()
  let last = 0
  for (const match of matches) {
    const idx = match.index ?? 0
    if (idx > last) {
      frag.appendChild(doc.createTextNode(text.slice(last, idx)))
    }
    const mark = doc.createElement('mark')
    mark.setAttribute(SEARCH_HIGHLIGHT_ATTR, '1')
    mark.textContent = match[0]
    frag.appendChild(mark)
    last = idx + match[0].length
  }
  if (last < text.length) {
    frag.appendChild(doc.createTextNode(text.slice(last)))
  }
  textNode.parentNode?.replaceChild(frag, textNode)
}

/**
 * Подсветка в уже санитизированном HTML: обход только text nodes.
 * Не вызывать на сыром HTML из API.
 */
export function highlightInSanitizedHtml(safeHtml: string, query: string): string {
  const tokens = tokenizeHighlightQuery(query)
  const re = buildTokenRegex(tokens)
  if (!re || !safeHtml.trim()) return safeHtml

  const doc = new DOMParser().parseFromString(`<div id="root">${safeHtml}</div>`, 'text/html')
  const root = doc.getElementById('root')
  if (!root) return safeHtml

  const walker = doc.createTreeWalker(root, NodeFilter.SHOW_TEXT)
  const textNodes: Text[] = []
  let node = walker.nextNode()
  while (node) {
    textNodes.push(node as Text)
    node = walker.nextNode()
  }

  for (const textNode of textNodes) {
    const parent = textNode.parentElement
    if (parent && (parent.closest('script') || parent.closest('style'))) continue
    // Уже внутри нашей подсветки — не дублировать
    if (parent?.tagName === 'MARK' && parent.hasAttribute(SEARCH_HIGHLIGHT_ATTR)) continue
    wrapMatchesInTextNode(textNode, re, doc)
  }

  return root.innerHTML
}

/** Есть ли хотя бы одно совпадение токенов в plain text. */
export function plainTextHasHighlight(text: string, query: string): boolean {
  const tokens = tokenizeHighlightQuery(query)
  const re = buildTokenRegex(tokens)
  if (!re || !text) return false
  re.lastIndex = 0
  return re.test(text)
}
