const DEFAULT_TOGGLE_TITLE = 'Новый раздел'

const EMPTY_HTML_SNIPPETS = new Set(['', '<p></p>', '<p><br></p>', '<p><br/></p>'])

export const RICH_MEDIA_IN_HTML = /\/api\/v1\/portal\/rich-media\/[0-9a-f-]{36}\/file/i
export const IMG_IN_HTML = /<img[\s>]/i

export function htmlHasEmbeddedRichMedia(html: string): boolean {
  return RICH_MEDIA_IN_HTML.test(html) || IMG_IN_HTML.test(html)
}

function normalizeVisibleText(text: string): string {
  return text.replace(/\u00a0/g, ' ').replace(/\s+/g, ' ').trim()
}

function stripHtmlTags(html: string): string {
  return normalizeVisibleText(html.replace(/<[^>]+>/g, ' '))
}

/** Проверка toggle-блоков без DOM (совместимо с Vitest node). */
function htmlHasVisibleContent(html: string): boolean {
  let remaining = html
  const togglePattern =
    /<details[^>]*class="[^"]*buildin-toggle[^"]*"[^>]*>([\s\S]*?)<\/details>/gi

  for (const match of html.matchAll(togglePattern)) {
    const inner = match[1] ?? ''
    const summaryMatch = inner.match(/<summary[^>]*>([\s\S]*?)<\/summary>/i)
    const bodyMatch = inner.match(
      /<div[^>]*class="[^"]*buildin-toggle-body[^"]*"[^>]*>([\s\S]*?)<\/div>/i,
    )
    const summaryText = stripHtmlTags(summaryMatch?.[1] ?? '')
    const bodyText = stripHtmlTags(bodyMatch?.[1] ?? '')
    if (bodyText.length > 0) {
      return true
    }
    if (summaryText.length > 0 && summaryText !== DEFAULT_TOGGLE_TITLE) {
      return true
    }
    remaining = remaining.replace(match[0], ' ')
  }

  return stripHtmlTags(remaining).length > 0 || htmlHasEmbeddedRichMedia(html)
}

export function buildinToggleBodyHasVisibleContent(body: Element | null): boolean {
  if (!body) return false
  const text = (body.textContent ?? '').replace(/\u00a0/g, ' ').trim()
  if (text.length > 0) return true
  return body.querySelector('img') !== null
}

/** Возвращает true, если HTML-строка не содержит видимого контента. */
export function isEmptyHtml(html: string): boolean {
  const normalized = html.trim()
  if (EMPTY_HTML_SNIPPETS.has(normalized)) {
    return true
  }

  if (typeof DOMParser !== 'undefined') {
    const doc = new DOMParser().parseFromString(normalized, 'text/html')
    const root = doc.body

    const toggles = root.querySelectorAll('details.buildin-toggle')
    for (const toggle of toggles) {
      if (buildinToggleBodyHasVisibleContent(toggle.querySelector('.buildin-toggle-body'))) {
        return false
      }
      const summaryText =
        toggle.querySelector('summary')?.textContent?.replace(/\u00a0/g, ' ').trim() ?? ''
      if (summaryText.length > 0 && summaryText !== DEFAULT_TOGGLE_TITLE) {
        return false
      }
      toggle.remove()
    }

    const plain = root.textContent?.replace(/\u00a0/g, ' ').trim() ?? ''
    if (plain.length > 0) {
      return false
    }
    if (root.querySelector('img[src]')) {
      return false
    }
    return !htmlHasEmbeddedRichMedia(normalized)
  }

  return !htmlHasVisibleContent(normalized)
}
