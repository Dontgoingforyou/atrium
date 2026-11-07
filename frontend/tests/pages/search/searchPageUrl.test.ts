import { describe, expect, it } from 'vitest'
import {
  parseTagSlugsFromSearchParams,
  setTagSlugsInSearchParams,
} from '../../../src/pages/search/searchPageUrl'

describe('searchPageUrl', () => {
  it('парсит tag_slug из URL', () => {
    const p = new URLSearchParams('tag_slug=urgent&tag_slug=review')
    expect(parseTagSlugsFromSearchParams(p)).toEqual(['urgent', 'review'])
  })

  it('пустые и дубли tag_slug', () => {
    const p = new URLSearchParams('tag_slug=&tag_slug=a&tag_slug=a')
    expect(parseTagSlugsFromSearchParams(p)).toEqual(['a'])
  })

  it('записывает теги в URLSearchParams', () => {
    const p = setTagSlugsInSearchParams(new URLSearchParams('q=test'), ['urgent', 'review'])
    expect(p.get('q')).toBe('test')
    expect(p.getAll('tag_slug')).toEqual(['urgent', 'review'])
  })

  it('очищает tag_slug, сохраняя q', () => {
    const p = setTagSlugsInSearchParams(
      new URLSearchParams('q=test&tag_slug=urgent'),
      [],
    )
    expect(p.get('q')).toBe('test')
    expect(p.getAll('tag_slug')).toEqual([])
  })
})
