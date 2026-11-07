import { sanitizeRichHtml } from '@/utils/html/sanitizeRichHtml'

/** Ключ для сравнения REST↔editor: sanitize, не сырой getHTML(). */
export function emittedRichHtmlKey(html: string): string {
  return sanitizeRichHtml(html)
}

export function rememberEmittedRichHtml(emitted: Set<string>, rawHtml: string): void {
  emitted.add(emittedRichHtmlKey(rawHtml))
}

export function shouldApplyExternalRichHtml(
  emitted: Set<string>,
  currentRawHtml: string,
  incomingRawHtml: string,
): boolean {
  const safeNext = sanitizeRichHtml(incomingRawHtml || '<p></p>')
  if (sanitizeRichHtml(currentRawHtml) === safeNext) return false
  if (emitted.delete(safeNext)) return false
  return true
}
