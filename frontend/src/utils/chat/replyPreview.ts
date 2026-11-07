import type { ChatMessage } from '../../types/chat'
import { normalizeReplyQuoteText } from './messageQuoteSelection'

/** Optimistic `reply_to` для отправки ответа (с опциональной цитатой). */
export function buildOptimisticReplyPreview(
  replyTo: ChatMessage | null,
  replyMid: string | null | undefined,
  quote: string | null | undefined,
): ChatMessage['reply_to'] {
  if (!replyTo || !replyMid || replyMid !== replyTo.id) return null
  const q = normalizeReplyQuoteText(quote)
  return {
    id: replyTo.id,
    author_sub: replyTo.author_sub,
    body: q || replyTo.body || '',
    deleted_for_all_at: replyTo.deleted_for_all_at,
    quote_text: q,
  }
}

/** Хендлеры ответа/цитаты без sync-effect на setState. */
export function createReplyStateHandlers(
  setReplyTo: (message: ChatMessage | null) => void,
  setReplyQuoteText: (quote: string | null) => void,
) {
  const clearReply = () => {
    setReplyTo(null)
    setReplyQuoteText(null)
  }
  const handleReply = (message: ChatMessage, quoteText?: string) => {
    setReplyTo(message)
    setReplyQuoteText(normalizeReplyQuoteText(quoteText))
  }
  return { handleReply, clearReply }
}
