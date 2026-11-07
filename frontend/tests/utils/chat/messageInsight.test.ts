import { describe, expect, it } from 'vitest'

import { insightAtLabel } from '@/utils/chat/chatDate'
import { mergeInsightRows, pluralRu, viewsLabel } from '@/utils/chat/messageInsight'

describe('mergeInsightRows', () => {
  it('отдаёт реакцию приоритетнее просмотра для одного пользователя', () => {
    const rows = mergeInsightRows(
      [{ emoji: '👍', reactors: [{ user_sub: 'a', reacted_at: '2026-08-10T12:00:00Z' }] }],
      [{ user_sub: 'a', read_at: '2026-08-10T11:00:00Z' }, { user_sub: 'b', read_at: '2026-08-10T10:00:00Z' }],
    )
    expect(rows).toHaveLength(2)
    expect(rows[0]).toMatchObject({ user_sub: 'a', kind: 'reaction', emoji: '👍' })
    expect(rows[1]).toMatchObject({ user_sub: 'b', kind: 'read' })
  })
})

describe('pluralRu / viewsLabel', () => {
  it('склоняет просмотры', () => {
    expect(viewsLabel(1)).toBe('1 просмотр')
    expect(viewsLabel(2)).toBe('2 просмотра')
    expect(viewsLabel(5)).toBe('5 просмотров')
    expect(pluralRu(21, 'реакция', 'реакции', 'реакций')).toBe('реакция')
  })
})

describe('insightAtLabel', () => {
  it('форматирует сегодня/вчера', () => {
    const now = new Date()
    const todayIso = now.toISOString()
    expect(insightAtLabel(todayIso)).toMatch(/^сегодня в /)

    const y = new Date(now)
    y.setDate(y.getDate() - 1)
    expect(insightAtLabel(y.toISOString())).toMatch(/^вчера в /)
  })
})
