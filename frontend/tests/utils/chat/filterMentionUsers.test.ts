import { describe, expect, it } from 'vitest'

import type { PortalUser } from '../../../src/types/user'
import { filterMentionUsers } from '../../../src/utils/chat/filterMentionUsers'

function user(partial: Partial<PortalUser> & Pick<PortalUser, 'sub'>): PortalUser {
  return {
    display_name: null,
    email: null,
    username: null,
    ...partial,
  }
}

describe('filterMentionUsers', () => {
  const users = [
    user({ sub: '1', display_name: 'Ada Holt' }),
    user({ sub: '2', display_name: 'Ben Cole' }),
    user({ sub: '3', display_name: 'Cora Lane' }),
    user({ sub: '4', display_name: 'Dana Moss' }),
    user({ sub: '5', display_name: 'Evan Brooks' }),
    user({ sub: '6', display_name: 'Faye Nolan' }),
    user({ sub: '7', display_name: 'Mira Holt' }),
    user({ sub: '8', email: 'manager@example.com' }),
  ]

  it('при пустом query возвращает всех кандидатов без hard-cap 6', () => {
    const result = filterMentionUsers(users, '')
    expect(result).toHaveLength(users.length)
    expect(result.map((u) => u.sub)).toContain('7')
    expect(result.map((u) => u.sub)).toContain('8')
  })

  it('фильтрует по подстроке display_name', () => {
    const result = filterMentionUsers(users, 'mira')
    expect(result.map((u) => u.sub)).toEqual(['7'])
  })

  it('фильтрует по email, если нет display_name', () => {
    const result = filterMentionUsers(users, 'manager@')
    expect(result.map((u) => u.sub)).toEqual(['8'])
  })

  it('нет совпадений → пустой список; спецсимволы query не ломают фильтр', () => {
    expect(filterMentionUsers(users, 'zzz-no-match')).toEqual([])
    expect(filterMentionUsers(users, '.*').map((u) => u.sub)).toEqual([])
  })
})
