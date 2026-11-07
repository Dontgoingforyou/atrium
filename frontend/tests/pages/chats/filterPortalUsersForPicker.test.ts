import { describe, expect, it } from 'vitest'

import { filterPortalUsersForPicker } from '@/pages/chats/filterPortalUsersForPicker'
import type { PortalUser } from '@/types/chat'

function user(over: Partial<PortalUser> & Pick<PortalUser, 'sub'>): PortalUser {
  return {
    email: null,
    username: null,
    display_name: null,
    avatar_url: null,
    avatar_focal_x: null,
    avatar_focal_y: null,
    presence: 'offline',
    last_seen_at: null,
    ...over,
  }
}

describe('filterPortalUsersForPicker', () => {
  const users = [
    user({ sub: 'me', display_name: 'Я' }),
    user({ sub: 'u1', display_name: 'Анна Петрова', email: 'anna@ex.com', username: 'anna' }),
    user({ sub: 'u2', display_name: 'Борис', email: 'boris@ex.com', username: 'boris' }),
  ]

  it('исключает текущего пользователя', () => {
    expect(filterPortalUsersForPicker(users, 'me', '').map((u) => u.sub)).toEqual(['u1', 'u2'])
  })

  it('фильтрует по display_name, email и username', () => {
    expect(filterPortalUsersForPicker(users, 'me', 'петр').map((u) => u.sub)).toEqual(['u1'])
    expect(filterPortalUsersForPicker(users, 'me', 'boris@').map((u) => u.sub)).toEqual(['u2'])
    expect(filterPortalUsersForPicker(users, 'me', 'ANNA').map((u) => u.sub)).toEqual(['u1'])
  })

  it('пустой поиск возвращает всех кроме себя', () => {
    expect(filterPortalUsersForPicker(users, null, '   ').map((u) => u.sub)).toEqual([
      'me',
      'u1',
      'u2',
    ])
  })
})
