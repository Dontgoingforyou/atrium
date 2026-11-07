import { describe, expect, it } from 'vitest'

import { applyChatEventToList, parseChatWsPayload } from '@/utils/chat/chatWs'

describe('parseChatWsPayload ephemeral', () => {
  it('не создаёт message_created для typing', () => {
    const e = parseChatWsPayload({
      event: 'typing',
      user_sub: 'u1',
      display_name: 'Alice',
      active: true,
    })
    expect(e.type).toBe('typing')
    expect(applyChatEventToList([{ id: '1' } as never], e)).toHaveLength(1)
  })

  it('envelope typing без message не даёт фантом', () => {
    const e = parseChatWsPayload({ event: 'typing', active: true })
    expect(e.type).toBe('typing')
  })
})
