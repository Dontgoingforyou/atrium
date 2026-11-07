import { describe, expect, it } from 'vitest'

import { applyChatEventToList } from '@/utils/chat/chatWs'
import type { ChatMessage } from '@/types/chat'

const base = (id: string): ChatMessage => ({
  id,
  chat_id: 'c1',
  author_sub: 'a',
  body: 'x',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: null,
  deleted_for_all_at: null,
  receipt: 'sent',
  reply_to_message_id: null,
  reply_to: null,
  reactions: [],
  forwarded_from: null,
})

describe('applyChatEventToList message_deleted', () => {
  it('удаляет сообщение из списка', () => {
    const prev = [base('m1'), base('m2')]
    const next = applyChatEventToList(prev, {
      type: 'message_deleted',
      message: { ...base('m1'), body: '', deleted_for_all_at: '2026-01-02T00:00:00Z' },
    })
    expect(next.map((m) => m.id)).toEqual(['m2'])
  })
})
