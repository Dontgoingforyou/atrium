/** Разбить текст на фрагменты: обычный текст и URL http(s). */
export type TextLinkPart = { type: 'text'; value: string } | { type: 'link'; value: string }

const URL_RE = /https?:\/\/[^\s<>"']+/gi

export function splitTextWithLinks(text: string): TextLinkPart[] {
  if (!text) return []
  const parts: TextLinkPart[] = []
  let last = 0
  for (const match of text.matchAll(URL_RE)) {
    const start = match.index ?? 0
    if (start > last) {
      parts.push({ type: 'text', value: text.slice(last, start) })
    }
    let url = match[0]
    while (/[.,;:!?)]$/.test(url)) {
      url = url.slice(0, -1)
    }
    if (url) parts.push({ type: 'link', value: url })
    last = start + url.length
  }
  if (last < text.length) {
    parts.push({ type: 'text', value: text.slice(last) })
  }
  return parts
}
