/** Протокол WS для онлайн emoji-pong (эфемерные события). */

export type EmojiPongInviteEvent = {
  type: 'emoji_pong_invite'
  user_sub: string
  display_name: string
  session_id: string
  emoji: string
}

export type EmojiPongAcceptEvent = {
  type: 'emoji_pong_accept'
  user_sub: string
  display_name: string
  session_id: string
}

export type EmojiPongDeclineEvent = {
  type: 'emoji_pong_decline'
  user_sub: string
  display_name: string
  session_id: string
}

export type EmojiPongPaddleEvent = {
  type: 'emoji_pong_paddle'
  user_sub: string
  display_name: string
  session_id: string
  paddle_x: number
}

export type EmojiPongStateEvent = {
  type: 'emoji_pong_state'
  user_sub: string
  display_name: string
  session_id: string
  ball_x: number
  ball_y: number
  vx: number
  vy: number
  host_paddle_x: number
  guest_paddle_x: number
  host_score: number
  guest_score: number
  finished: boolean
}

export type EmojiPongEndEvent = {
  type: 'emoji_pong_end'
  user_sub: string
  display_name: string
  session_id: string
  host_score: number
  guest_score: number
}

export type EmojiPongWsEvent =
  | EmojiPongInviteEvent
  | EmojiPongAcceptEvent
  | EmojiPongDeclineEvent
  | EmojiPongPaddleEvent
  | EmojiPongStateEvent
  | EmojiPongEndEvent

const EMOJI_PONG_EVENTS = new Set([
  'emoji_pong_invite',
  'emoji_pong_accept',
  'emoji_pong_decline',
  'emoji_pong_paddle',
  'emoji_pong_state',
  'emoji_pong_end',
])

export function isEmojiPongEventName(event: string): event is EmojiPongWsEvent['type'] {
  return EMOJI_PONG_EVENTS.has(event)
}

function num(v: unknown, fallback = 0): number {
  return typeof v === 'number' && Number.isFinite(v) ? v : fallback
}

function str(v: unknown): string {
  return typeof v === 'string' ? v : ''
}

/** Разбор emoji_pong_* из сырого WS JSON (уже с полем event). */
export function parseEmojiPongWsEvent(raw: Record<string, unknown>): EmojiPongWsEvent | null {
  const event = str(raw.event)
  if (!isEmojiPongEventName(event)) return null
  const base = {
    user_sub: str(raw.user_sub),
    display_name: str(raw.display_name),
    session_id: str(raw.session_id),
  }
  if (!base.session_id) return null

  if (event === 'emoji_pong_invite') {
    const emoji = str(raw.emoji)
    if (!emoji) return null
    return { type: event, ...base, emoji }
  }
  if (event === 'emoji_pong_accept' || event === 'emoji_pong_decline') {
    return { type: event, ...base }
  }
  if (event === 'emoji_pong_paddle') {
    return { type: event, ...base, paddle_x: Math.min(1, Math.max(0, num(raw.paddle_x, 0.5))) }
  }
  if (event === 'emoji_pong_state') {
    return {
      type: event,
      ...base,
      ball_x: Math.min(1, Math.max(0, num(raw.ball_x, 0.5))),
      ball_y: Math.min(1, Math.max(0, num(raw.ball_y, 0.3))),
      vx: num(raw.vx),
      vy: num(raw.vy),
      host_paddle_x: Math.min(1, Math.max(0, num(raw.host_paddle_x, 0.35))),
      guest_paddle_x: Math.min(1, Math.max(0, num(raw.guest_paddle_x, 0.65))),
      host_score: Math.max(0, Math.floor(num(raw.host_score))),
      guest_score: Math.max(0, Math.floor(num(raw.guest_score))),
      finished: Boolean(raw.finished),
    }
  }
  if (event === 'emoji_pong_end') {
    return {
      type: event,
      ...base,
      host_score: Math.max(0, Math.floor(num(raw.host_score))),
      guest_score: Math.max(0, Math.floor(num(raw.guest_score))),
    }
  }
  return null
}
