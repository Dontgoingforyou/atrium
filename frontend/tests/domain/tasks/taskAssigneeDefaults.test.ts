import { describe, expect, it } from 'vitest'

import { resolveDefaultTaskAssigneeSubs } from '../../../src/domain/tasks/taskAssigneeDefaults'

describe('resolveDefaultTaskAssigneeSubs', () => {
  it('на чужой доске (team + фильтр) назначает владельца доски, не текущего пользователя', () => {
    expect(resolveDefaultTaskAssigneeSubs('team', ['board-owner'], 'me')).toEqual(['board-owner'])
  })

  it('при нескольких исполнителях в фильтре команды сохраняет всех', () => {
    expect(resolveDefaultTaskAssigneeSubs('team', ['a', 'b'], 'me')).toEqual(['a', 'b'])
  })

  it('в своих задачах назначает текущего пользователя', () => {
    expect(resolveDefaultTaskAssigneeSubs('my', ['board-owner'], 'me')).toEqual(['me'])
  })

  it('в команде без фильтра назначает текущего пользователя', () => {
    expect(resolveDefaultTaskAssigneeSubs('team', [], 'me')).toEqual(['me'])
  })

  it('без текущего пользователя и без фильтра возвращает пустой список', () => {
    expect(resolveDefaultTaskAssigneeSubs('my', [], undefined)).toEqual([])
  })

  it('team + фильтр без currentUser — всё равно владельцы фильтра', () => {
    expect(resolveDefaultTaskAssigneeSubs('team', ['owner'], undefined)).toEqual(['owner'])
  })

  it('не мутирует исходный filterAssigneeSubs', () => {
    const filter = ['a', 'b'] as const
    const out = resolveDefaultTaskAssigneeSubs('team', filter, 'me')
    expect(out).toEqual(['a', 'b'])
    expect(out).not.toBe(filter)
    expect(filter).toEqual(['a', 'b'])
  })
})
