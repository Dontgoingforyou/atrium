import {
  EMOJI_PONG_BALL_RADIUS_RATIO,
  EMOJI_PONG_PADDLE_HEIGHT_RATIO,
  EMOJI_PONG_PADDLE_WIDTH_RATIO,
  EMOJI_PONG_PLAY_TOP_RATIO,
  EMOJI_PONG_WINS_TO_FINISH,
} from '@/utils/chat/emojiOnlyMessage'
import { EmojiCatchGameResult } from './EmojiCatchGameResult'
import { EmojiCatchScoreboard, type EmojiPongPlayer } from './EmojiCatchScoreboard'
import type { EmojiCatchGameProps } from './emojiCatchGameTypes'
import { useEmojiCatchGameEngine } from './useEmojiCatchGameEngine'
import styles from '@/styles/modules/chat/EmojiCatchGame.module.css'

/**
 * Игровое поле emoji-ponga. Движок (физика, net-sync, ввод) — в
 * {@link useEmojiCatchGameEngine}; здесь только рендер и сборка табло.
 */
export function EmojiCatchGame(props: EmojiCatchGameProps) {
  const { peer, me, shareEnabled, sharePending, shareError, onShareScore, onClose } = props
  const {
    isOnline,
    isGuest,
    ballEmoji,
    hostScore,
    guestScore,
    soloScore,
    finished,
    playAgain,
    movePaddleToClientX,
    fieldRef,
    scoreElRef,
    ballElRef,
    peerPaddleElRef,
    myPaddleElRef,
  } = useEmojiCatchGameEngine(props)

  const displayMyScore = isOnline ? (isGuest ? guestScore : hostScore) : soloScore
  const displayPeerScore = isOnline ? (isGuest ? hostScore : guestScore) : peer.bestScore
  const scoreboardPeer: EmojiPongPlayer = {
    ...peer,
    bestScore: isOnline ? displayPeerScore : peer.bestScore,
  }
  const scoreboardMe: EmojiPongPlayer = {
    ...me,
    bestScore: isOnline ? displayMyScore : Math.max(me.bestScore, soloScore),
  }

  if (finished) {
    return (
      <EmojiCatchGameResult
        emoji={ballEmoji}
        score={displayMyScore}
        shareEnabled={shareEnabled}
        sharePending={sharePending}
        shareError={shareError}
        onShare={() => onShareScore(displayMyScore)}
        onPlayAgain={playAgain}
        onClose={onClose}
      />
    )
  }

  const paddleWPct = EMOJI_PONG_PADDLE_WIDTH_RATIO * 100
  const paddleHPct = EMOJI_PONG_PADDLE_HEIGHT_RATIO * 100
  const ballSizePct = EMOJI_PONG_BALL_RADIUS_RATIO * 2 * 100

  return (
    <div className={styles.game}>
      <div
        ref={fieldRef}
        className={styles.field}
        aria-label="Игровое поле"
        onPointerDown={(e) => {
          movePaddleToClientX(e.clientX)
          if (e.pointerType === 'mouse') {
            if (document.pointerLockElement !== e.currentTarget) {
              void e.currentTarget.requestPointerLock?.()
            }
          } else {
            e.currentTarget.setPointerCapture(e.pointerId)
          }
        }}
      >
        <EmojiCatchScoreboard
          peer={scoreboardPeer}
          me={scoreboardMe}
          sessionScore={displayMyScore}
        />
        <div ref={scoreElRef} className={styles.scoreBackdrop} aria-hidden>
          {displayMyScore}
        </div>
        <div
          ref={ballElRef}
          className={styles.ball}
          style={{
            left: '50%',
            top: '50%',
            width: `${ballSizePct}%`,
            height: `${ballSizePct}%`,
          }}
          aria-hidden
        >
          {ballEmoji}
        </div>
        {isOnline ? (
          <div
            ref={peerPaddleElRef}
            className={`${styles.paddle} ${styles.paddlePeer}`}
            style={{
              left: '50%',
              width: `${paddleWPct}%`,
              height: `${paddleHPct}%`,
              top: `${EMOJI_PONG_PLAY_TOP_RATIO * 100 + 2}%`,
            }}
            aria-hidden
          />
        ) : null}
        <div
          ref={myPaddleElRef}
          className={`${styles.paddle} ${styles.paddleMine}`}
          style={{
            left: '50%',
            width: `${paddleWPct}%`,
            height: `${paddleHPct}%`,
            bottom: `${EMOJI_PONG_PADDLE_HEIGHT_RATIO * 120}%`,
          }}
          aria-hidden
        />
      </div>
      <p className={styles.hint}>
        {isOnline
          ? `Вместе до ${EMOJI_PONG_WINS_TO_FINISH}: вы снизу, соперник сверху`
          : 'Клик по полю — захват курсора'}
      </p>
    </div>
  )
}
