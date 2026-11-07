import { describe, expect, it } from 'vitest'

import type { ChatMessage } from '@/types/chat'
import {
  applyChatEventToList,
  normalizeChatMessage,
  parseChatWsPayload,
  patchOwnReceiptFromWs,
} from '@/utils/chat/chatWs'

const base = (id: string, partial: Partial<ChatMessage> = {}): ChatMessage => ({
  id,
  chat_id: 'c1',
  author_sub: 'a',
  body: 'x',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: null,
  deleted_for_all_at: null,
  receipt: null,
  reply_to_message_id: null,
  reply_to: null,
  reactions: [],
  forwarded_from: null,
  ...partial,
})

describe('normalizeChatMessage', () => {
  it('нормализует reply_to, forwarded_from и reactions', () => {
    const m = normalizeChatMessage({
      id: 1,
      chat_id: 'c1',
      author_sub: 'u',
      body: null,
      created_at: 't',
      receipt: 'read',
      reply_to: { id: 'r1', author_sub: 'b', body: 'hi' },
      forwarded_from: { author_sub: 'f', source_message_id: '' },
      reactions: [{ emoji: '👍', count: '2', reacted_by_me: 1 }],
    })
    expect(m).not.toBeNull()
    expect(m!.id).toBe('1')
    expect(m!.body).toBe('')
    expect(m!.receipt).toBe('read')
    expect(m!.reply_to).toEqual({
      id: 'r1',
      author_sub: 'b',
      body: 'hi',
      deleted_for_all_at: null,
      quote_text: null,
    })
    expect(m!.reply_quote_text).toBeNull()
    expect(m!.forwarded_from).toEqual({ author_sub: 'f', source_message_id: null })
    expect(m!.reactions).toEqual([{ emoji: '👍', count: 2, reacted_by_me: true }])
  })

  it('отбрасывает не-объект и реакции без emoji / с NaN count', () => {
    expect(normalizeChatMessage(null)).toBeNull()
    expect(normalizeChatMessage([])).toBeNull()
    const m = normalizeChatMessage({
      id: 'm1',
      chat_id: 'c1',
      author_sub: 'u',
      body: '',
      created_at: 't',
      reactions: [{ emoji: '', count: 1 }, { emoji: '🔥', count: Number.NaN }, { count: 1 }],
    })
    expect(m?.reactions).toEqual([{ emoji: '🔥', count: 0, reacted_by_me: false }])
  })
})

describe('parseChatWsPayload', () => {
  it('envelope: message_created / meta / deleted / reactions', () => {
    expect(
      parseChatWsPayload({
        event: 'message_created',
        message: { id: 'm1', chat_id: 'c', author_sub: 'u', body: 'hi', created_at: 't' },
      }).type,
    ).toBe('message_created')

    expect(parseChatWsPayload({ event: 'members_updated' })).toEqual({ type: 'members_updated' })
    expect(parseChatWsPayload({ event: 'chat_meta_updated', chat_id: 'c1', title: 'T' })).toEqual({
      type: 'chat_meta_updated',
      chat_id: 'c1',
      title: 'T',
    })
    expect(parseChatWsPayload({ event: 'chat_deleted', chat_id: 'c1' })).toEqual({
      type: 'chat_deleted',
      chat_id: 'c1',
    })
    expect(
      parseChatWsPayload({
        event: 'message_reactions_updated',
        message_id: 'm1',
        reactions: [{ emoji: '🔥', count: 1, reacted_by_me: false }],
      }),
    ).toEqual({
      type: 'message_reactions_updated',
      message_id: 'm1',
      reactions: [{ emoji: '🔥', count: 1, reacted_by_me: false }],
    })
  })

  it('envelope без message → ignored', () => {
    expect(parseChatWsPayload({ event: 'message_created' })).toEqual({
      type: 'ignored',
    })
  })

  it('неизвестный event не маскируется под read_state_updated', () => {
    expect(parseChatWsPayload({ event: 'not_a_real_event' })).toEqual({ type: 'ignored' })
    expect(parseChatWsPayload({ event: 'emoji_pong_invite' })).toEqual({ type: 'ignored' })
  })

  it('chat_deleted / chat_meta_updated без chat_id → ignored', () => {
    expect(parseChatWsPayload({ event: 'chat_deleted' })).toEqual({ type: 'ignored' })
    expect(parseChatWsPayload({ event: 'chat_deleted', chat_id: '' })).toEqual({ type: 'ignored' })
    expect(parseChatWsPayload({ event: 'chat_meta_updated' })).toEqual({ type: 'ignored' })
  })

  it('legacy плоский объект → message_created', () => {
    const e = parseChatWsPayload({
      id: 'm2',
      chat_id: 'c',
      author_sub: 'u',
      body: 'x',
      created_at: 't',
    })
    expect(e.type).toBe('message_created')
    if (e.type === 'message_created') expect(e.message.id).toBe('m2')
  })

  it('не-объект, ping-shape и объект без id/chat_id → ignored', () => {
    expect(parseChatWsPayload(null)).toEqual({ type: 'ignored' })
    expect(parseChatWsPayload({ type: 'ping' })).toEqual({ type: 'ignored' })
    expect(parseChatWsPayload({ foo: 1 })).toEqual({ type: 'ignored' })
    expect(parseChatWsPayload({ id: 'm1' })).toEqual({ type: 'ignored' })
  })
})

describe('applyChatEventToList', () => {
  it('message_created убирает optimistic того же автора', () => {
    const prev = [base('optimistic-1', { author_sub: 'u' }), base('m0', { author_sub: 'other' })]
    const next = applyChatEventToList(prev, {
      type: 'message_created',
      message: base('m1', { author_sub: 'u', body: 'real' }),
    })
    expect(next.map((m) => m.id)).toEqual(['m0', 'm1'])
  })

  it('message_updated заменяет или добавляет', () => {
    expect(
      applyChatEventToList([base('m1')], {
        type: 'message_updated',
        message: base('m1', { body: 'edited' }),
      })[0]!.body,
    ).toBe('edited')
    expect(
      applyChatEventToList([base('m1')], {
        type: 'message_updated',
        message: base('m2', { body: 'new' }),
      }).map((m) => m.id),
    ).toEqual(['m1', 'm2'])
  })

  it('message_reactions_updated', () => {
    const next = applyChatEventToList([base('m1')], {
      type: 'message_reactions_updated',
      message_id: 'm1',
      reactions: [{ emoji: '👍', count: 1, reacted_by_me: true }],
    })
    expect(next[0]!.reactions).toEqual([{ emoji: '👍', count: 1, reacted_by_me: true }])
  })

  it('ignored и read_state не меняют список', () => {
    const prev = [base('m1')]
    expect(applyChatEventToList(prev, { type: 'ignored' })).toBe(prev)
    expect(applyChatEventToList(prev, { type: 'read_state_updated' })).toEqual(prev)
  })
})

describe('patchOwnReceiptFromWs', () => {
  it('проставляет sent для своих сообщений без receipt', () => {
    const list = [base('m1', { author_sub: 'me', receipt: null })]
    const next = patchOwnReceiptFromWs(
      list,
      { type: 'message_created', message: base('m1', { author_sub: 'me', receipt: null }) },
      'me',
    )
    expect(next[0]!.receipt).toBe('sent')
  })

  it('не трогает чужие и read_state', () => {
    const list = [base('m1', { author_sub: 'other' })]
    expect(
      patchOwnReceiptFromWs(
        list,
        { type: 'message_created', message: base('m1', { author_sub: 'other' }) },
        'me',
      ),
    ).toBe(list)
    expect(patchOwnReceiptFromWs(list, { type: 'read_state_updated' }, 'me')).toBe(list)
  })
})
