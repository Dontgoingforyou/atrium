import { useCallback, useEffect, useRef, useState } from 'react'

import {
  EMOJI_PONG_BALL_RADIUS_RATIO,
  EMOJI_PONG_PADDLE_SYNC_MS,
  EMOJI_PONG_PADDLE_WIDTH_RATIO,
  EMOJI_PONG_PLAY_TOP_RATIO,
  EMOJI_PONG_SPEED_INITIAL,
  EMOJI_PONG_STATE_SYNC_MS,
  EMOJI_PONG_WINS_TO_FINISH,
} from '@/utils/chat/emojiOnlyMessage'
import {
  bounceOffPaddle,
  currentSpeed,
  hitPaddle,
  makeServe,
  normalizeVelocity,
  paddleYBottom,
  paddleYTop,
  type BallState,
} from './emojiPongPhysics'
import type { EmojiCatchGameProps } from './emojiCatchGameTypes'
import { useEmojiCatchGuestTick, useEmojiCatchInput, useEmojiCatchPaint } from './useEmojiCatchRuntime'

const PADDLE_LERP = 0.35

/**
 * Solo / online versus. Кадры и net-sync — через refs + RAF (без setState на каждый пакет WS).
 *
 * Владеет всей «движковой» частью игры: refs, счёт, RAF-циклы физики (host/solo и guest),
 * net-sync по matchTick, ввод ракетки (pointer/keyboard/cursor-lock). Компонент
 * {@link EmojiCatchGame} отвечает только за рендер.
 */
export function useEmojiCatchGameEngine(props: EmojiCatchGameProps) {
  const {
    emojis,
    onlineRole = null,
    netRef = null,
    matchTick = 0,
    onSendState,
    onSendPaddle,
    onSendEnd,
  } = props
  const isOnline = onlineRole != null
  const isGuest = onlineRole === 'guest'
  const flipView = isGuest
  const ballEmoji = emojis[0] ?? '😀'

  const fieldRef = useRef<HTMLDivElement>(null)
  const ballElRef = useRef<HTMLDivElement>(null)
  const myPaddleElRef = useRef<HTMLDivElement>(null)
  const peerPaddleElRef = useRef<HTMLDivElement>(null)
  const scoreElRef = useRef<HTMLDivElement>(null)

  const myPaddleXRef = useRef(0.5)
  const peerPaddleXRef = useRef(0.5)
  const hostScoreRef = useRef(0)
  const guestScoreRef = useRef(0)
  const soloScoreRef = useRef(0)
  const finishedRef = useRef(false)
  const lastStateSentRef = useRef(0)
  const lastPaddleSentRef = useRef(0)
  const lastTsRef = useRef<number | null>(null)
  const rafRef = useRef(0)
  const onSendStateRef = useRef(onSendState)
  const onSendPaddleRef = useRef(onSendPaddle)
  const onSendEndRef = useRef(onSendEnd)
  const ballRef = useRef<BallState>({
    x: 0.5,
    y: 0.5,
    vx: 0.2,
    vy: EMOJI_PONG_SPEED_INITIAL,
  })

  const [hostScore, setHostScore] = useState(0)
  const [guestScore, setGuestScore] = useState(0)
  const [soloScore, setSoloScore] = useState(0)
  const [finished, setFinished] = useState(false)
  const [roundId, setRoundId] = useState(0)

  useEffect(() => {
    onSendStateRef.current = onSendState
    onSendPaddleRef.current = onSendPaddle
    onSendEndRef.current = onSendEnd
  })

  const { paint, syncScoreDom } = useEmojiCatchPaint({
    flipView,
    isGuest,
    isOnline,
    ballRef,
    ballElRef,
    myPaddleElRef,
    peerPaddleElRef,
    scoreElRef,
    myPaddleXRef,
    peerPaddleXRef,
    hostScoreRef,
    guestScoreRef,
    soloScoreRef,
  })

  const endMatch = useCallback(() => {
    if (finishedRef.current) return
    finishedRef.current = true
    setFinished(true)
    cancelAnimationFrame(rafRef.current)
    if (isOnline && !isGuest) {
      onSendEndRef.current?.(hostScoreRef.current, guestScoreRef.current)
      onSendStateRef.current?.({
        ball_x: ballRef.current.x,
        ball_y: ballRef.current.y,
        vx: 0,
        vy: 0,
        host_paddle_x: myPaddleXRef.current,
        guest_paddle_x: peerPaddleXRef.current,
        host_score: hostScoreRef.current,
        guest_score: guestScoreRef.current,
        finished: true,
      })
    }
  }, [isGuest, isOnline])

  const serveBall = useCallback(
    (towardBottom: boolean) => {
      ballRef.current = makeServe(
        towardBottom,
        hostScoreRef.current + guestScoreRef.current + soloScoreRef.current,
      )
      paint()
    },
    [paint],
  )

  const playAgain = useCallback(() => {
    if (isOnline) return
    cancelAnimationFrame(rafRef.current)
    finishedRef.current = false
    soloScoreRef.current = 0
    hostScoreRef.current = 0
    guestScoreRef.current = 0
    myPaddleXRef.current = 0.5
    setSoloScore(0)
    setHostScore(0)
    setGuestScore(0)
    setFinished(false)
    setRoundId((id) => id + 1)
  }, [isOnline])

  const applyMyPaddle = useCallback(
    (next: number) => {
      if (finishedRef.current) return
      myPaddleXRef.current = next
      const el = myPaddleElRef.current
      if (el) el.style.left = `${next * 100}%`
      if (isOnline && onSendPaddleRef.current) {
        const now = performance.now()
        if (now - lastPaddleSentRef.current >= EMOJI_PONG_PADDLE_SYNC_MS) {
          lastPaddleSentRef.current = now
          onSendPaddleRef.current(next)
        }
      }
    },
    [isOnline],
  )

  const movePaddleByDelta = useCallback(
    (deltaClientX: number) => {
      const el = fieldRef.current
      if (!el || finishedRef.current) return
      const rect = el.getBoundingClientRect()
      if (rect.width <= 0) return
      const half = EMOJI_PONG_PADDLE_WIDTH_RATIO / 2
      applyMyPaddle(
        Math.min(1 - half, Math.max(half, myPaddleXRef.current + deltaClientX / rect.width)),
      )
    },
    [applyMyPaddle],
  )

  const movePaddleToClientX = useCallback(
    (clientX: number) => {
      const el = fieldRef.current
      if (!el || finishedRef.current) return
      const rect = el.getBoundingClientRect()
      if (rect.width <= 0) return
      const half = EMOJI_PONG_PADDLE_WIDTH_RATIO / 2
      applyMyPaddle(Math.min(1 - half, Math.max(half, (clientX - rect.left) / rect.width)))
    },
    [applyMyPaddle],
  )

  // Редкий matchTick: подтянуть счёт/финиш из netRef (без ререндера на каждый пакет)
  useEffect(() => {
    if (!isOnline || !netRef) return
    const snap = netRef.current.snapshot
    if (!snap) return
    if (snap.host_score !== hostScoreRef.current) {
      hostScoreRef.current = snap.host_score
      setHostScore(snap.host_score)
    }
    if (snap.guest_score !== guestScoreRef.current) {
      guestScoreRef.current = snap.guest_score
      setGuestScore(snap.guest_score)
    }
    syncScoreDom()
    if (snap.finished && !finishedRef.current) {
      finishedRef.current = true
      setFinished(true)
    }
  }, [isOnline, matchTick, netRef, syncScoreDom])

  // Host / solo physics
  useEffect(() => {
    if (isGuest) return

    myPaddleXRef.current = 0.5
    peerPaddleXRef.current = 0.5
    hostScoreRef.current = 0
    guestScoreRef.current = 0
    soloScoreRef.current = 0
    finishedRef.current = false
    lastTsRef.current = null
    serveBall(true)

    const tick = (ts: number) => {
      if (finishedRef.current) return
      const prev = lastTsRef.current ?? ts
      lastTsRef.current = ts
      const dt = Math.min(0.05, (ts - prev) / 1000)

      if (isOnline && netRef) {
        const target = netRef.current.remotePaddleX
        peerPaddleXRef.current += (target - peerPaddleXRef.current) * PADDLE_LERP
      }

      const points = hostScoreRef.current + guestScoreRef.current + soloScoreRef.current
      const speed = currentSpeed(points)
      let { x, y, vx, vy } = ballRef.current
      ;({ vx, vy } = normalizeVelocity(vx, vy, speed))
      x += vx * dt
      y += vy * dt

      const ballR = EMOJI_PONG_BALL_RADIUS_RATIO
      const playTop = EMOJI_PONG_PLAY_TOP_RATIO
      const bottomY = paddleYBottom()
      const topY = paddleYTop()
      const hostPx = myPaddleXRef.current
      const guestPx = isOnline ? peerPaddleXRef.current : hostPx

      if (x - ballR <= 0) {
        x = ballR
        vx = Math.abs(vx)
      } else if (x + ballR >= 1) {
        x = 1 - ballR
        vx = -Math.abs(vx)
      }

      const applyBounce = (px: number, fromBottom: boolean) => {
        const next = bounceOffPaddle(x, y, px, fromBottom, points + (isOnline ? 0 : 1))
        x = next.x
        y = next.y
        vx = next.vx
        vy = next.vy
        if (!isOnline) {
          soloScoreRef.current += 1
          setSoloScore(soloScoreRef.current)
          syncScoreDom()
        }
      }

      if (isOnline) {
        if (hitPaddle(x, y, vy, hostPx, bottomY, true)) {
          applyBounce(hostPx, true)
        } else if (hitPaddle(x, y, vy, guestPx, topY, false)) {
          applyBounce(guestPx, false)
        } else if (y - ballR > 1.02) {
          guestScoreRef.current += 1
          setGuestScore(guestScoreRef.current)
          syncScoreDom()
          if (guestScoreRef.current >= EMOJI_PONG_WINS_TO_FINISH) {
            ballRef.current = { x, y, vx, vy }
            paint()
            endMatch()
            return
          }
          serveBall(false)
          rafRef.current = requestAnimationFrame(tick)
          return
        } else if (y + ballR < playTop - 0.02) {
          hostScoreRef.current += 1
          setHostScore(hostScoreRef.current)
          syncScoreDom()
          if (hostScoreRef.current >= EMOJI_PONG_WINS_TO_FINISH) {
            ballRef.current = { x, y, vx, vy }
            paint()
            endMatch()
            return
          }
          serveBall(true)
          rafRef.current = requestAnimationFrame(tick)
          return
        }
      } else if (hitPaddle(x, y, vy, hostPx, bottomY, true)) {
        applyBounce(hostPx, true)
      } else if (y - ballR > 1.02) {
        ballRef.current = { x, y, vx, vy }
        paint()
        endMatch()
        return
      } else if (y - ballR <= playTop) {
        y = playTop + ballR
        vy = Math.abs(vy)
      }

      ballRef.current = { x, y, vx, vy }
      paint()

      if (isOnline && onSendStateRef.current) {
        const now = performance.now()
        if (now - lastStateSentRef.current >= EMOJI_PONG_STATE_SYNC_MS) {
          lastStateSentRef.current = now
          onSendStateRef.current({
            ball_x: x,
            ball_y: y,
            vx,
            vy,
            host_paddle_x: hostPx,
            guest_paddle_x: guestPx,
            host_score: hostScoreRef.current,
            guest_score: guestScoreRef.current,
            finished: false,
          })
        }
      }

      rafRef.current = requestAnimationFrame(tick)
    }

    rafRef.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(rafRef.current)
  }, [endMatch, isGuest, isOnline, netRef, paint, roundId, serveBall, syncScoreDom])

  // Guest: экстраполяция по velocity между пакетами WS (~50 Гц → визуально 60)
  useEmojiCatchGuestTick({
    isGuest,
    finished,
    netRef,
    paint,
    roundId,
    ballRef,
    peerPaddleXRef,
    lastTsRef,
    rafRef,
    finishedRef,
  })

  useEmojiCatchInput({
    fieldRef,
    finished,
    roundId,
    finishedRef,
    movePaddleByDelta,
    movePaddleToClientX,
    applyMyPaddle,
    myPaddleXRef,
  })

  return {
    fieldRef,
    ballElRef,
    myPaddleElRef,
    peerPaddleElRef,
    scoreElRef,
    hostScore,
    guestScore,
    soloScore,
    finished,
    roundId,
    isOnline,
    isGuest,
    ballEmoji,
    playAgain,
    movePaddleToClientX,
    movePaddleByDelta,
    applyMyPaddle,
  }
}

export type EmojiCatchGameEngine = ReturnType<typeof useEmojiCatchGameEngine>
