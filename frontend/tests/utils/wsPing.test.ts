import { describe, expect, it } from 'vitest'

import { isWsPing, WS_PONG_MESSAGE } from '@/utils/wsPing'

describe('isWsPing', () => {
  it('распознаёт серверный keepalive ping', () => {
    expect(isWsPing('{"type":"ping"}')).toBe(true)
  })

  it('игнорирует прочие сообщения', () => {
    expect(isWsPing('{"type":"pong"}')).toBe(false)
    expect(isWsPing('{"event":"message_created"}')).toBe(false)
    expect(isWsPing('{')).toBe(false)
    expect(isWsPing(null)).toBe(false)
  })

  it('ответ клиенту — JSON pong', () => {
    expect(JSON.parse(WS_PONG_MESSAGE)).toEqual({ type: 'pong' })
  })
})
