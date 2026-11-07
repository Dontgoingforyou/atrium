import { describe, expect, it } from 'vitest'

import type { Chat } from '@/types/chat'
import { dmPeerSub } from '@/utils/chat/dmPeerSub'

function chat(partial: Pick<Chat, 'is_direct' | 'member_subs'>): Chat {
  return {
    id: 'c1',
    title: null,
    created_by_sub: 'owner',
    created_at: '',
    updated_at: '',
    unread_count: 0,
    version: 1,
    ...partial,
  }
}

describe('dmPeerSub', () => {
  it('для DM возвращает собеседника', () => {
    expect(dmPeerSub(chat({ is_direct: true, member_subs: ['me', 'other'] }), 'me')).toBe('other')
  })

  it('без currentSub или для группы — null', () => {
    expect(dmPeerSub(chat({ is_direct: true, member_subs: ['me', 'other'] }), null)).toBeNull()
    expect(dmPeerSub(chat({ is_direct: false, member_subs: ['me', 'other'] }), 'me')).toBeNull()
  })

  it('чужой sub не в member_subs — null (не подставлять чужого peer)', () => {
    expect(dmPeerSub(chat({ is_direct: true, member_subs: ['a', 'b'] }), 'stranger')).toBeNull()
  })

  it('один участник (нет peer) — null', () => {
    expect(dmPeerSub(chat({ is_direct: true, member_subs: ['me'] }), 'me')).toBeNull()
  })
})
