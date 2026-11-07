import { describe, expect, it } from 'vitest'

import { isSemanticUnavailableError, parseSearchMode } from '@/utils/search/semanticSearchError'

describe('parseSearchMode', () => {
  it('только semantic остаётся semantic, иначе fulltext', () => {
    expect(parseSearchMode('semantic')).toBe('semantic')
    expect(parseSearchMode('fulltext')).toBe('fulltext')
    expect(parseSearchMode('other')).toBe('fulltext')
    expect(parseSearchMode(null)).toBe('fulltext')
  })
})

describe('isSemanticUnavailableError', () => {
  it('true только для двух фраз из util', () => {
    expect(isSemanticUnavailableError(new Error('OPENAI_API_KEY не задан'))).toBe(true)
    expect(isSemanticUnavailableError(new Error('Семантический поиск недоступен'))).toBe(true)
    expect(isSemanticUnavailableError(new Error('Сервис временно недоступен. Попробуйте позже.'))).toBe(false)
    expect(isSemanticUnavailableError(new Error('Failed to fetch'))).toBe(false)
  })
})
