import { describe, expect, it } from 'vitest'
import {
  pruneActiveTypes,
  searchPageHasMore,
  searchResultsShownRange,
  visibleSearchEntityTypes,
} from '../../../src/pages/search/searchPageHelpers'
import type { SearchEntityType } from '../../../src/types/search'

describe('visibleSearchEntityTypes', () => {
  it('убирает замороженный тип learning_material', () => {
    const types: SearchEntityType[] = ['document', 'learning_material', 'task']
    expect(visibleSearchEntityTypes(types)).toEqual(['document', 'task'])
  })

  it('не меняет список без замороженных типов', () => {
    const types: SearchEntityType[] = ['document', 'task']
    expect(visibleSearchEntityTypes(types)).toEqual(['document', 'task'])
  })
})

describe('pruneActiveTypes', () => {
  it('оставляет только типы, допустимые в новом режиме', () => {
    const active: SearchEntityType[] = ['document', 'learning_material', 'specialist_note']
    const allowed: SearchEntityType[] = ['document', 'task', 'chat_message']
    expect(pruneActiveTypes(active, allowed)).toEqual(['document'])
  })

  it('возвращает пустой список, если ни один тип не допустим', () => {
    expect(pruneActiveTypes(['specialist_note'], ['document', 'task'])).toEqual([])
  })
})

describe('searchPageHasMore', () => {
  it('для semantic использует total_found, а не длину страницы', () => {
    expect(
      searchPageHasMore({ resultCount: 20, pageSize: 20, skip: 0, totalFound: 20 }),
    ).toBe(false)
    expect(
      searchPageHasMore({ resultCount: 20, pageSize: 20, skip: 0, totalFound: 21 }),
    ).toBe(true)
  })

  it('для fulltext без total считает по размеру страницы', () => {
    expect(searchPageHasMore({ resultCount: 20, pageSize: 20, skip: 0 })).toBe(true)
    expect(searchPageHasMore({ resultCount: 7, pageSize: 20, skip: 0 })).toBe(false)
  })
})

describe('searchResultsShownRange', () => {
  it('считает диапазон «показано» от skip', () => {
    expect(searchResultsShownRange({ skip: 20, resultCount: 5 })).toEqual({ from: 21, to: 25 })
  })
})
