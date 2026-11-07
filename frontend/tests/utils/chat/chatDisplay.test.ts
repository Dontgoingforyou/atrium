import { describe, expect, it } from 'vitest'

import type { Chat } from '../../../src/types/chat'
import { chatDisplayName } from '../../../src/utils/chat/chatDisplay'

function chat(partial: Pick<Chat, 'is_direct' | 'title' | 'member_subs'>): Chat {
  return {
    id: 'c1',
    created_by_sub: 'owner',
    created_at: '',
    updated_at: '',
    unread_count: 0,
    version: 1,
    ...partial,
  }
}

describe('chatDisplayName', () => {
  it('DM — имя собеседника из userMap', () => {
    const dm = chat({
      is_direct: true,
      title: null,
      member_subs: ['me', 'other'],
    })
    expect(chatDisplayName(dm, 'me', { other: 'Иван' })).toBe('Иван')
    expect(chatDisplayName(dm, 'me', {})).toBe('...')
  })

  it('группа — title или без названия', () => {
    expect(
      chatDisplayName(chat({ is_direct: false, title: 'Team', member_subs: [] }), 'me', {}),
    ).toBe('Team')
    expect(
      chatDisplayName(chat({ is_direct: false, title: null, member_subs: [] }), 'me', {}),
    ).toBe('(без названия)')
  })
})
