import { describe, expect, it } from 'vitest'

import {
  isChatsNarrowViewport,
  shouldClearActiveChatOnBackToList,
  CHATS_NARROW_MAX_WIDTH_PX,
} from '@/pages/chats/chatsPageLayout'

describe('isChatsNarrowViewport', () => {
  it('узкий при ширине ≤ брейкпоинта 900', () => {
    expect(isChatsNarrowViewport(CHATS_NARROW_MAX_WIDTH_PX)).toBe(true)
    expect(isChatsNarrowViewport(901)).toBe(false)
    expect(isChatsNarrowViewport(320)).toBe(true)
  })
})

describe('shouldClearActiveChatOnBackToList', () => {
  it('на узком экране сбрасывает чат только если уходим из пикера/группы', () => {
    expect(shouldClearActiveChatOnBackToList('picker', true)).toBe(true)
    expect(shouldClearActiveChatOnBackToList('groupPicker', true)).toBe(true)
    expect(shouldClearActiveChatOnBackToList('list', true)).toBe(false)
  })

  it('на широком экране не сбрасывает активный чат', () => {
    expect(shouldClearActiveChatOnBackToList('picker', false)).toBe(false)
    expect(shouldClearActiveChatOnBackToList('groupPicker', false)).toBe(false)
  })
})
