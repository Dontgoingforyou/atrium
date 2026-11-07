import type { MutableRefObject } from 'react'

import type { EmojiPongNetBus, EmojiPongOnlineRole } from '@/hooks/useEmojiPongOnline'

import type { EmojiPongPlayer } from './EmojiCatchScoreboard'

export type OnlineStatePayload = {
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

export type EmojiCatchGameProps = {
  emojis: string[]
  peer: EmojiPongPlayer
  me: EmojiPongPlayer
  shareEnabled: boolean
  sharePending: boolean
  shareError: string | null
  onShareScore: (score: number) => void
  onClose: () => void
  onlineRole?: EmojiPongOnlineRole | null
  /** Высокочастотный канал WS — без React-ререндеров. */
  netRef?: MutableRefObject<EmojiPongNetBus> | null
  matchTick?: number
  onSendPaddle?: (x: number) => void
  onSendState?: (state: OnlineStatePayload) => void
  onSendEnd?: (hostScore: number, guestScore: number) => void
}
