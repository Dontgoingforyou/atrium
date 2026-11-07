import { describe, expect, it } from 'vitest'

import { firstNonEmptyColumnStatus } from '@/domain/kanban/kanbanOverdueFocus'

describe('firstNonEmptyColumnStatus', () => {
  it('возвращает первую колонку с задачами в порядке отображения', () => {
    const counts = new Map([
      ['todo', 0],
      ['wip', 3],
      ['done', 5],
    ])
    expect(firstNonEmptyColumnStatus(['todo', 'wip', 'done'], counts)).toBe('wip')
  })

  it('возвращает null когда все колонки пусты', () => {
    const counts = new Map([
      ['todo', 0],
      ['wip', 0],
    ])
    expect(firstNonEmptyColumnStatus(['todo', 'wip'], counts)).toBeNull()
  })

  it('возвращает null при пустом порядке колонок', () => {
    expect(firstNonEmptyColumnStatus([], new Map())).toBeNull()
  })

  it('колонки без записи в счётчиках считаются пустыми', () => {
    const counts = new Map([['todo', 0]])
    expect(firstNonEmptyColumnStatus(['todo', 'done'], counts)).toBeNull()
  })
})
