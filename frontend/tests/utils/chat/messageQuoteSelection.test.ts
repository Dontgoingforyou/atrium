// @vitest-environment jsdom
import { describe, expect, it, afterEach } from 'vitest'

import {
  CHAT_REPLY_QUOTE_TEXT_MAX_LENGTH,
  getSelectedTextInElement,
  normalizeReplyQuoteText,
} from '@/utils/chat/messageQuoteSelection'

describe('normalizeReplyQuoteText', () => {
  it('возвращает null для пустой строки и пробелов', () => {
    expect(normalizeReplyQuoteText('')).toBeNull()
    expect(normalizeReplyQuoteText('   ')).toBeNull()
    expect(normalizeReplyQuoteText(null)).toBeNull()
  })

  it('обрезает до лимита бэкенда', () => {
    const long = 'а'.repeat(CHAT_REPLY_QUOTE_TEXT_MAX_LENGTH + 50)
    const out = normalizeReplyQuoteText(long)
    expect(out).toHaveLength(CHAT_REPLY_QUOTE_TEXT_MAX_LENGTH)
  })
})

describe('getSelectedTextInElement', () => {
  afterEach(() => {
    window.getSelection()?.removeAllRanges()
  })

  it('возвращает null без выделения', () => {
    const el = document.createElement('div')
    el.textContent = 'привет'
    document.body.appendChild(el)
    expect(getSelectedTextInElement(el)).toBeNull()
    el.remove()
  })

  it('возвращает текст выделения внутри контейнера', () => {
    const el = document.createElement('div')
    el.textContent = 'привет мир'
    document.body.appendChild(el)
    const textNode = el.firstChild as Text
    const range = document.createRange()
    range.setStart(textNode, 0)
    range.setEnd(textNode, 6)
    const sel = window.getSelection()
    sel?.removeAllRanges()
    sel?.addRange(range)
    expect(getSelectedTextInElement(el)).toBe('привет')
    el.remove()
  })

  it('возвращает null если контейнер null', () => {
    expect(getSelectedTextInElement(null)).toBeNull()
  })

  it('возвращает null если выделение вне контейнера', () => {
    const inside = document.createElement('div')
    inside.textContent = 'внутри'
    const outside = document.createElement('div')
    outside.textContent = 'снаружи'
    document.body.append(inside, outside)
    const textNode = outside.firstChild as Text
    const range = document.createRange()
    range.selectNodeContents(textNode)
    window.getSelection()?.removeAllRanges()
    window.getSelection()?.addRange(range)
    expect(getSelectedTextInElement(inside)).toBeNull()
    inside.remove()
    outside.remove()
  })
})
