// @vitest-environment jsdom

import { afterEach, describe, expect, it } from 'vitest'

import { CHAT_FREQUENT_REACTIONS_KEY } from '../../../src/constants/chatStorage'
import {
  getQuickReactionEmojis,
  recordReactionEmojiUse,
} from '../../../src/utils/chat/chatReactionFrequent'

afterEach(() => {
  localStorage.clear()
})

describe('chatReactionFrequent', () => {
  it('без storage — дефолтный набор из 8', () => {
    expect(getQuickReactionEmojis()).toHaveLength(8)
    expect(getQuickReactionEmojis()[0]).toBe('👍')
  })

  it('recordReactionEmojiUse поднимает эмодзи в начало', () => {
    recordReactionEmojiUse('🚀')
    const list = getQuickReactionEmojis()
    expect(list[0]).toBe('🚀')
    expect(list).toHaveLength(8)
  })

  it('пустой emoji игнорируется', () => {
    recordReactionEmojiUse('   ')
    expect(localStorage.getItem(CHAT_FREQUENT_REACTIONS_KEY)).toBeNull()
  })

  it('слишком длинную строку не пишет в storage', () => {
    recordReactionEmojiUse('x'.repeat(33))
    expect(localStorage.getItem(CHAT_FREQUENT_REACTIONS_KEY)).toBeNull()
  })
})
