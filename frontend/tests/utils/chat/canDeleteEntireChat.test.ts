import { describe, expect, it } from 'vitest'

import type { Chat } from '../../../src/types/chat'
import { canDeleteEntireChat } from '../../../src/utils/chat/canDeleteEntireChat'

function chat(partial: Pick<Chat, 'is_direct' | 'created_by_sub'> & Partial<Pick<Chat, 'member_subs'>>): Chat {
  return {
    id: 'c1',
    title: 't',
    created_at: '',
    updated_at: '',
    member_subs: partial.member_subs ?? ['owner', 'other'],
    unread_count: 0,
    version: 1,
    ...partial,
  }
}

describe('canDeleteEntireChat', () => {
  it('без currentUserSub → false', () => {
    expect(canDeleteEntireChat(chat({ is_direct: true, created_by_sub: 'a' }), null)).toBe(false)
  })

  it('не участник → false (и DM, и группа)', () => {
    expect(
      canDeleteEntireChat(
        chat({ is_direct: true, created_by_sub: 'owner', member_subs: ['owner', 'peer'] }),
        'stranger',
      ),
    ).toBe(false)
    expect(
      canDeleteEntireChat(
        chat({ is_direct: false, created_by_sub: 'owner', member_subs: ['owner'] }),
        'stranger',
      ),
    ).toBe(false)
  })

  it('DM — любой участник с sub может удалить', () => {
    expect(
      canDeleteEntireChat(
        chat({ is_direct: true, created_by_sub: 'owner', member_subs: ['owner', 'other'] }),
        'other',
      ),
    ).toBe(true)
  })

  it('группа — только создатель', () => {
    const group = chat({
      is_direct: false,
      created_by_sub: 'owner',
      member_subs: ['owner', 'member'],
    })
    expect(canDeleteEntireChat(group, 'owner')).toBe(true)
    expect(canDeleteEntireChat(group, 'member')).toBe(false)
  })
})
