import { describe, expect, it } from 'vitest'

import { chatsPageHref } from '../../../src/utils/chat/chatsNavigation'

describe('chatsPageHref', () => {
  it('без chatId → /chats', () => {
    expect(chatsPageHref()).toBe('/chats')
    expect(chatsPageHref(null)).toBe('/chats')
    expect(chatsPageHref('')).toBe('/chats')
  })

  it('с chat и message', () => {
    expect(chatsPageHref('c1')).toBe('/chats?chat=c1')
    expect(chatsPageHref('c1', 'm1')).toBe('/chats?chat=c1&message=m1')
  })

  it('кодирует спецсимволы в id (не ломает query)', () => {
    expect(chatsPageHref('c1&x=1', 'm=2')).toBe('/chats?chat=c1%26x%3D1&message=m%3D2')
  })
})
