import { describe, expect, it, vi } from 'vitest'

import type { ChatMessage } from '@/types/chat'
import { CHAT_REPLY_QUOTE_TEXT_MAX_LENGTH } from '@/utils/chat/messageQuoteSelection'
import { buildOptimisticReplyPreview, createReplyStateHandlers } from '@/utils/chat/replyPreview'

describe('buildOptimisticReplyPreview', () => {
  const msg = {
    id: 'm1',
    author_sub: 'u1',
    body: 'полный текст',
    deleted_for_all_at: null,
  } as ChatMessage

  it('собирает preview с цитатой', () => {
    expect(buildOptimisticReplyPreview(msg, 'm1', 'полный')).toEqual({
      id: 'm1',
      author_sub: 'u1',
      body: 'полный',
      deleted_for_all_at: null,
      quote_text: 'полный',
    })
  })

  it('возвращает null при несовпадении id', () => {
    expect(buildOptimisticReplyPreview(msg, 'other', 'x')).toBeNull()
  })
})

describe('createReplyStateHandlers', () => {
  it('handleReply нормализует цитату, clearReply сбрасывает оба поля', () => {
    const setReplyTo = vi.fn()
    const setReplyQuoteText = vi.fn()
    const { handleReply, clearReply } = createReplyStateHandlers(setReplyTo, setReplyQuoteText)
    const msg = { id: 'm1', author_sub: 'u', body: 'текст' } as ChatMessage
    handleReply(msg, '  цитата  ')
    expect(setReplyTo).toHaveBeenCalledWith(msg)
    expect(setReplyQuoteText).toHaveBeenCalledWith('цитата')
    clearReply()
    expect(setReplyTo).toHaveBeenLastCalledWith(null)
    expect(setReplyQuoteText).toHaveBeenLastCalledWith(null)
  })

  it('handleReply обрезает слишком длинную цитату', () => {
    const setReplyTo = vi.fn()
    const setReplyQuoteText = vi.fn()
    const { handleReply } = createReplyStateHandlers(setReplyTo, setReplyQuoteText)
    const msg = { id: 'm1', author_sub: 'u', body: 'текст' } as ChatMessage
    const long = 'я'.repeat(CHAT_REPLY_QUOTE_TEXT_MAX_LENGTH + 200)
    handleReply(msg, long)
    const quote = setReplyQuoteText.mock.calls[0]![0] as string
    expect(quote).toHaveLength(CHAT_REPLY_QUOTE_TEXT_MAX_LENGTH)
  })
})
