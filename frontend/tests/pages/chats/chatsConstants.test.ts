import { describe, expect, it } from 'vitest'

import { CHAT_ID_FROM_URL_RE } from '@/pages/chats/chatsConstants'

describe('CHAT_ID_FROM_URL_RE', () => {
  it('принимает UUID', () => {
    expect(CHAT_ID_FROM_URL_RE.test('550e8400-e29b-41d4-a716-446655440000')).toBe(true)
  })

  it('отклоняет пустую строку, путь и не-UUID', () => {
    expect(CHAT_ID_FROM_URL_RE.test('')).toBe(false)
    expect(CHAT_ID_FROM_URL_RE.test('../chats')).toBe(false)
    expect(CHAT_ID_FROM_URL_RE.test('not-a-uuid')).toBe(false)
    expect(CHAT_ID_FROM_URL_RE.test('550e8400-e29b-41d4-a716-446655440000/extra')).toBe(false)
  })
})
