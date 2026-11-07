import { describe, expect, it } from 'vitest'

import { formatSimilarityBadge } from '@/utils/search/formatSimilarityBadge'

describe('formatSimilarityBadge', () => {
  it('подписывает процент как похожесть, не как совпадение слов', () => {
    expect(formatSimilarityBadge(0.31)).toBe('похожесть 31%')
    expect(formatSimilarityBadge(0.91)).toBe('похожесть 91%')
  })
})
