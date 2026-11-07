import { describe, expect, it } from 'vitest'

import {
  formatEmojiGameScoreCaption,
  formatEmojiGameScoreDigits,
  formatEmojiGameScoreMessage,
  bestEmojiGameScoresByAuthor,
  isEmojiOnlyMessage,
  parseEmojiGameScoreMessage,
  parseEmojiOnlyBody,
} from '@/utils/chat/emojiOnlyMessage'

describe('parseEmojiOnlyBody / isEmojiOnlyMessage', () => {
  it('один эмодзи — true', () => {
    expect(isEmojiOnlyMessage('🏀')).toBe(true)
    expect(parseEmojiOnlyBody('🏀')).toEqual({ emojis: ['🏀'] })
  })

  it('два и три эмодзи — true', () => {
    expect(isEmojiOnlyMessage('🔥🔥')).toBe(true)
    expect(parseEmojiOnlyBody('🔥🔥')).toEqual({ emojis: ['🔥', '🔥'] })
    expect(isEmojiOnlyMessage('😀😎🎉')).toBe(true)
    expect(parseEmojiOnlyBody('😀😎🎉')?.emojis).toHaveLength(3)
  })

  it('четыре эмодзи — false', () => {
    expect(isEmojiOnlyMessage('😀😎🎉🏀')).toBe(false)
    expect(parseEmojiOnlyBody('😀😎🎉🏀')).toBeNull()
  })

  it('текст с эмодзи — false', () => {
    expect(isEmojiOnlyMessage('привет 🏀')).toBe(false)
    expect(isEmojiOnlyMessage('🏀 гол')).toBe(false)
    expect(isEmojiOnlyMessage('a')).toBe(false)
  })

  it('пробелы по краям игнорируются', () => {
    expect(isEmojiOnlyMessage('  🏀  ')).toBe(true)
    expect(parseEmojiOnlyBody('  🔥🔥  ')).toEqual({ emojis: ['🔥', '🔥'] })
  })

  it('пустая строка и только пробелы — false', () => {
    expect(isEmojiOnlyMessage('')).toBe(false)
    expect(isEmojiOnlyMessage('   ')).toBe(false)
    expect(parseEmojiOnlyBody('')).toBeNull()
  })

  it('ZWJ-последовательность считается одним grapheme', () => {
    const family = '👨‍👩‍👧'
    expect(isEmojiOnlyMessage(family)).toBe(true)
    expect(parseEmojiOnlyBody(family)).toEqual({ emojis: [family] })
  })

  it('флаг (два regional indicator) — один grapheme', () => {
    expect(isEmojiOnlyMessage('🇷🇺')).toBe(true)
    expect(parseEmojiOnlyBody('🇷🇺')?.emojis).toHaveLength(1)
  })
})

describe('formatEmojiGameScoreMessage / parseEmojiGameScoreMessage', () => {
  it('формирует и разбирает текст результата для чата', () => {
    expect(formatEmojiGameScoreMessage('🏀', 42)).toBe('🏀 Игра: 42')
    expect(parseEmojiGameScoreMessage('🏀 Игра: 42')).toEqual({ emoji: '🏀', score: 42 })
    expect(parseEmojiGameScoreMessage('🔥 Игра: 0')).toEqual({ emoji: '🔥', score: 0 })
    expect(parseEmojiGameScoreMessage('просто текст')).toBeNull()
    expect(parseEmojiGameScoreMessage(`🏀 Игра: ${'9'.repeat(400)}`)).toBeNull()
  })

  it('подпись для UI — кто и сколько', () => {
    expect(formatEmojiGameScoreCaption('Вы', 21)).toBe('Вы: 21')
    expect(formatEmojiGameScoreCaption('Анна', 10)).toBe('Анна: 10')
  })

  it('три цифры счёта и лучшие по авторам', () => {
    expect(formatEmojiGameScoreDigits(25)).toBe('025')
    expect(formatEmojiGameScoreDigits(0)).toBe('000')
    expect(
      bestEmojiGameScoresByAuthor([
        { author_sub: 'a', body: '😀 Игра: 10' },
        { author_sub: 'a', body: '😀 Игра: 21' },
        { author_sub: 'b', body: '😀 Игра: 5' },
        { author_sub: 'b', body: 'не счёт' },
      ]),
    ).toEqual({ a: 21, b: 5 })
  })
})
