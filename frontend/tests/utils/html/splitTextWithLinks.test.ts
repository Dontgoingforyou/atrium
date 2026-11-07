import { describe, expect, it } from 'vitest'

import { splitTextWithLinks } from '@/utils/html/splitTextWithLinks'

describe('splitTextWithLinks', () => {
  it('возвращает текст без ссылок как один фрагмент', () => {
    expect(splitTextWithLinks('телемост')).toEqual([{ type: 'text', value: 'телемост' }])
  })

  it('выделяет http(s) URL', () => {
    expect(splitTextWithLinks('см. https://telemost.yandex.ru/j/123 и всё')).toEqual([
      { type: 'text', value: 'см. ' },
      { type: 'link', value: 'https://telemost.yandex.ru/j/123' },
      { type: 'text', value: ' и всё' },
    ])
  })

  it('отрезает хвостовую пунктуацию', () => {
    expect(splitTextWithLinks('ссылка https://example.com.')).toEqual([
      { type: 'text', value: 'ссылка ' },
      { type: 'link', value: 'https://example.com' },
      { type: 'text', value: '.' },
    ])
  })

  it('не превращает javascript: URL в ссылку (XSS-контракт)', () => {
    const parts = splitTextWithLinks('см. javascript:alert(1) и data:text/html,<script>')
    expect(parts.every((p) => p.type === 'text')).toBe(true)
    expect(parts.some((p) => p.type === 'link')).toBe(false)
  })
})
