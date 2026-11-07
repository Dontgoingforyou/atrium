import { describe, expect, it } from 'vitest'

import { isEmojiPongEventName, parseEmojiPongWsEvent } from '@/utils/chat/emojiPongWs'

describe('isEmojiPongEventName', () => {
  it('узнаёт события протокола', () => {
    expect(isEmojiPongEventName('emoji_pong_invite')).toBe(true)
    expect(isEmojiPongEventName('emoji_pong_paddle')).toBe(true)
    expect(isEmojiPongEventName('typing')).toBe(false)
  })
})

describe('parseEmojiPongWsEvent', () => {
  it('разбирает invite', () => {
    expect(
      parseEmojiPongWsEvent({
        event: 'emoji_pong_invite',
        user_sub: 'u1',
        display_name: 'Аня',
        session_id: 'sess-1234',
        emoji: '🏀',
      }),
    ).toEqual({
      type: 'emoji_pong_invite',
      user_sub: 'u1',
      display_name: 'Аня',
      session_id: 'sess-1234',
      emoji: '🏀',
    })
  })

  it('клампит paddle_x', () => {
    expect(
      parseEmojiPongWsEvent({
        event: 'emoji_pong_paddle',
        user_sub: 'u1',
        display_name: 'Аня',
        session_id: 'sess-1234',
        paddle_x: 1.5,
      }),
    ).toMatchObject({ paddle_x: 1 })
  })

  it('отклоняет без session_id', () => {
    expect(
      parseEmojiPongWsEvent({
        event: 'emoji_pong_accept',
        user_sub: 'u1',
        display_name: 'Аня',
      }),
    ).toBeNull()
  })

  it('invite без emoji / не-объект → null', () => {
    expect(
      parseEmojiPongWsEvent({
        event: 'emoji_pong_invite',
        user_sub: 'u1',
        display_name: 'Аня',
        session_id: 'sess-1',
        emoji: '',
      }),
    ).toBeNull()
    expect(parseEmojiPongWsEvent({ event: 'typing' } as Record<string, unknown>)).toBeNull()
  })

  it('разбирает state', () => {
    const parsed = parseEmojiPongWsEvent({
      event: 'emoji_pong_state',
      user_sub: 'u1',
      display_name: 'Аня',
      session_id: 'sess-1234',
      ball_x: 0.4,
      ball_y: 0.5,
      vx: 0.1,
      vy: -0.2,
      host_paddle_x: 0.3,
      guest_paddle_x: 0.7,
      host_score: 2,
      guest_score: 1,
      finished: false,
    })
    expect(parsed).toMatchObject({
      type: 'emoji_pong_state',
      ball_x: 0.4,
      host_score: 2,
      guest_score: 1,
      finished: false,
    })
  })

  it('клампит координаты мяча', () => {
    expect(
      parseEmojiPongWsEvent({
        event: 'emoji_pong_state',
        user_sub: 'u1',
        display_name: 'Аня',
        session_id: 'sess-1234',
        ball_x: 4,
        ball_y: -1,
      }),
    ).toMatchObject({ ball_x: 1, ball_y: 0 })
  })
})
