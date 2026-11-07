import { useState, type MutableRefObject } from 'react'

import { Modal } from '../../ui/Modal'
import {
  EMOJI_PONG_GAME_TITLE,
  EMOJI_PONG_MODAL_MAX_WIDTH_PX,
} from '@/utils/chat/emojiOnlyMessage'
import type {
  EmojiPongIncomingInvite,
  EmojiPongLiveSession,
  EmojiPongNetBus,
} from '@/hooks/useEmojiPongOnline'
import { EmojiCatchGame } from './EmojiCatchGame'
import type { EmojiPongPlayer } from './EmojiCatchScoreboard'
import styles from '@/styles/modules/chat/EmojiCatchGame.module.css'

type Props = {
  emojis: string[]
  peer: EmojiPongPlayer
  me: EmojiPongPlayer
  shareEnabled: boolean
  sharePending: boolean
  shareError: string | null
  onShareScore: (score: number) => void
  onClose: () => void
  /** DM: можно пригласить собеседника. */
  canPlayOnline?: boolean
  liveSession?: EmojiPongLiveSession | null
  waitingForAccept?: boolean
  incomingInvite?: EmojiPongIncomingInvite | null
  netRef?: MutableRefObject<EmojiPongNetBus> | null
  matchTick?: number
  onInviteOnline?: (emoji: string) => string | null | undefined
  onAcceptInvite?: () => void
  onDeclineInvite?: () => void
  onSendPaddle?: (x: number) => void
  onSendState?: (state: {
    ball_x: number
    ball_y: number
    vx: number
    vy: number
    host_paddle_x: number
    guest_paddle_x: number
    host_score: number
    guest_score: number
    finished: boolean
  }) => void
  onSendEnd?: (hostScore: number, guestScore: number) => void
  onClearOnlineSession?: () => void
}

type Phase = 'choose' | 'waiting' | 'play'

/** Модалка пасхалки emoji-pong (solo / online). */
export function EmojiCatchGameModal({
  emojis,
  peer,
  me,
  shareEnabled,
  sharePending,
  shareError,
  onShareScore,
  onClose,
  canPlayOnline = false,
  liveSession = null,
  waitingForAccept = false,
  incomingInvite = null,
  netRef = null,
  matchTick = 0,
  onInviteOnline,
  onAcceptInvite,
  onDeclineInvite,
  onSendPaddle,
  onSendState,
  onSendEnd,
  onClearOnlineSession,
}: Props) {
  const ballEmoji = emojis[0] ?? '😀'
  const onlinePlaying = Boolean(liveSession?.playing)
  /** Ручной выбор «Один» / экран выбора; waiting/play online — из пропсов. */
  const [manualPhase, setManualPhase] = useState<Phase>(() =>
    canPlayOnline ? 'choose' : 'play',
  )
  const phase: Phase = onlinePlaying
    ? 'play'
    : waitingForAccept
      ? 'waiting'
      : manualPhase

  const handleClose = () => {
    onClearOnlineSession?.()
    onClose()
  }

  const chooseTogether = () => {
    onInviteOnline?.(ballEmoji)
  }

  return (
    <Modal
      title={EMOJI_PONG_GAME_TITLE}
      maxWidth={EMOJI_PONG_MODAL_MAX_WIDTH_PX}
      onClose={handleClose}
      closeOnBackdrop={!sharePending}
    >
      <div className={styles.modalBody}>
        {phase === 'choose' ? (
          <div className={styles.result}>
            <p className={styles.resultEmoji} aria-hidden>
              {ballEmoji}
            </p>
            {incomingInvite ? (
              <>
                <p className={styles.resultScore}>
                  {incomingInvite.fromName} приглашает в игру
                </p>
                <div className={styles.resultActions}>
                  <button type="button" className="btn-primary" onClick={() => onAcceptInvite?.()}>
                    Принять
                  </button>
                  <button
                    type="button"
                    className={styles.secondaryBtn}
                    onClick={() => onDeclineInvite?.()}
                  >
                    Отклонить
                  </button>
                  <button
                    type="button"
                    className={styles.secondaryBtn}
                    onClick={() => setManualPhase('play')}
                  >
                    Один
                  </button>
                </div>
              </>
            ) : (
              <>
                <p className={styles.resultScore}>Как сыграем?</p>
                <div className={styles.resultActions}>
                  <button
                    type="button"
                    className="btn-primary"
                    onClick={() => setManualPhase('play')}
                  >
                    Один
                  </button>
                  <button type="button" className={styles.secondaryBtn} onClick={chooseTogether}>
                    Вместе
                  </button>
                </div>
              </>
            )}
          </div>
        ) : null}

        {phase === 'waiting' ? (
          <div className={styles.result}>
            <p className={styles.resultEmoji} aria-hidden>
              {ballEmoji}
            </p>
            {incomingInvite ? (
              <>
                <p className={styles.resultScore}>
                  {incomingInvite.fromName} тоже готов — принять?
                </p>
                <div className={styles.resultActions}>
                  <button type="button" className="btn-primary" onClick={() => onAcceptInvite?.()}>
                    Принять
                  </button>
                  <button
                    type="button"
                    className={styles.secondaryBtn}
                    onClick={() => {
                      onClearOnlineSession?.()
                      setManualPhase('choose')
                    }}
                  >
                    Отмена
                  </button>
                </div>
              </>
            ) : (
              <>
                <p className={styles.resultScore}>Ждём собеседника…</p>
                <div className={styles.resultActions}>
                  <button
                    type="button"
                    className={styles.secondaryBtn}
                    onClick={() => {
                      onClearOnlineSession?.()
                      setManualPhase('choose')
                    }}
                  >
                    Отмена
                  </button>
                </div>
              </>
            )}
          </div>
        ) : null}

        {phase === 'play' ? (
          <EmojiCatchGame
            emojis={emojis}
            peer={peer}
            me={me}
            shareEnabled={shareEnabled && !liveSession}
            sharePending={sharePending}
            shareError={shareError}
            onShareScore={onShareScore}
            onClose={handleClose}
            onlineRole={liveSession?.playing ? liveSession.role : null}
            netRef={netRef}
            matchTick={matchTick}
            onSendPaddle={onSendPaddle}
            onSendState={onSendState}
            onSendEnd={onSendEnd}
          />
        ) : null}
      </div>
    </Modal>
  )
}
