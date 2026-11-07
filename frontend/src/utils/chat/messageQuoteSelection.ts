export const CHAT_REPLY_QUOTE_TEXT_MAX_LENGTH = 1000

/** Подсветка фрагмента после прыжка по цитате — синхрон с `--duration-reply-quote-hit`. */
export const REPLY_JUMP_HIGHLIGHT_MS = 2800

/** Сколько ждать появления целевого сообщения в ленте перед отменой localJump. */
export const REPLY_JUMP_PENDING_TIMEOUT_MS = 5_000

export function normalizeReplyQuoteText(raw: string | null | undefined): string | null {
  if (raw == null) return null
  const text = raw.replace(/\u00a0/g, ' ').trim()
  if (!text) return null
  return text.length > CHAT_REPLY_QUOTE_TEXT_MAX_LENGTH
    ? text.slice(0, CHAT_REPLY_QUOTE_TEXT_MAX_LENGTH)
    : text
}

/** Выделение внутри контейнера (обычно узел текста сообщения), с нормализацией цитаты. */
export function getSelectedTextInElement(container: HTMLElement | null): string | null {
  if (!container) return null
  const sel = window.getSelection()
  if (!sel || sel.isCollapsed || sel.rangeCount === 0) return null
  const range = sel.getRangeAt(0)
  const common = range.commonAncestorContainer
  const node = common.nodeType === Node.TEXT_NODE ? common.parentElement : (common as Element)
  if (!node || !container.contains(node)) return null
  return normalizeReplyQuoteText(sel.toString())
}
