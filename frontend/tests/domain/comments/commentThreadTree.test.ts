import { describe, expect, it } from 'vitest'

import { removeCommentById } from '../../../src/domain/comments/commentThreadTree'
import type { ThreadComment } from '../../../src/types/commentThread'

function makeComment(overrides: Partial<ThreadComment> = {}): ThreadComment {
  return {
    id: 'c-1',
    parent_id: null,
    author_sub: 'user-a',
    body: 'Текст',
    mentions: [],
    version: 1,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    replies: [],
    ...overrides,
  }
}

describe('removeCommentById', () => {
  it('убирает комментарий верхнего уровня по id', () => {
    const comments = [makeComment({ id: 'c-1' }), makeComment({ id: 'c-2' })]

    const result = removeCommentById(comments, 'c-1')

    expect(result.map((c) => c.id)).toEqual(['c-2'])
  })

  it('убирает вложенный ответ, не трогая родителя и остальные ответы', () => {
    const comments = [
      makeComment({
        id: 'c-1',
        replies: [makeComment({ id: 'r-1', parent_id: 'c-1' }), makeComment({ id: 'r-2', parent_id: 'c-1' })],
      }),
    ]

    const result = removeCommentById(comments, 'r-1')

    expect(result).toHaveLength(1)
    expect(result[0].id).toBe('c-1')
    expect(result[0].replies.map((r) => r.id)).toEqual(['r-2'])
  })

  it('не изменяет комментарии без совпадения по id (в т.ч. без вложенных ответов)', () => {
    const comments = [makeComment({ id: 'c-1' }), makeComment({ id: 'c-2', replies: [makeComment({ id: 'r-1' })] })]

    const result = removeCommentById(comments, 'unknown-id')

    expect(result).toEqual(comments)
  })

  it('возвращает ту же ссылку, если ничего не удалено (без лишних ре-рендеров)', () => {
    const comments = [makeComment({ id: 'c-1', replies: [makeComment({ id: 'r-1' })] })]

    expect(removeCommentById(comments, 'unknown-id')).toBe(comments)
  })

  it('убирает глубоко вложенный ответ (3 уровня), сохраняя остальных', () => {
    const comments = [
      makeComment({
        id: 'c-1',
        replies: [
          makeComment({
            id: 'r-1',
            parent_id: 'c-1',
            replies: [makeComment({ id: 'rr-1', parent_id: 'r-1' }), makeComment({ id: 'rr-2', parent_id: 'r-1' })],
          }),
        ],
      }),
    ]

    const result = removeCommentById(comments, 'rr-1')

    expect(result).toHaveLength(1)
    expect(result[0].id).toBe('c-1')
    expect(result[0].replies[0].id).toBe('r-1')
    expect(result[0].replies[0].replies.map((r) => r.id)).toEqual(['rr-2'])
  })
})
