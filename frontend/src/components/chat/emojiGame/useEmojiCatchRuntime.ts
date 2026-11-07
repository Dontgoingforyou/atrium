import { useCallback, useEffect, type MutableRefObject } from 'react'

import { EMOJI_PONG_PADDLE_WIDTH_RATIO } from '@/utils/chat/emojiOnlyMessage'
import type { EmojiPongNetBus } from '@/hooks/useEmojiPongOnline'
import type { BallState } from './emojiPongPhysics'

const PADDLE_LERP = 0.35
const GUEST_EXTRAPOLATE_MAX_SEC = 0.12

type NetRef = MutableRefObject<EmojiPongNetBus> | null

/**
 * DOM-отрисовка: позиция мяча/ракеток и синхронизация счёта в текстовый узел.
 * Возвращает `viewY` (зеркальное отображение для guest), `paint`, `syncScoreDom`.
 */
export function useEmojiCatchPaint({
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
}: {
  flipView: boolean
  isGuest: boolean
  isOnline: boolean
  ballRef: MutableRefObject<BallState>
  ballElRef: MutableRefObject<HTMLDivElement | null>
  myPaddleElRef: MutableRefObject<HTMLDivElement | null>
  peerPaddleElRef: MutableRefObject<HTMLDivElement | null>
  scoreElRef: MutableRefObject<HTMLDivElement | null>
  myPaddleXRef: MutableRefObject<number>
  peerPaddleXRef: MutableRefObject<number>
  hostScoreRef: MutableRefObject<number>
  guestScoreRef: MutableRefObject<number>
  soloScoreRef: MutableRefObject<number>
}) {
  const viewY = useCallback(
    (worldY: number) => (flipView ? 1 - worldY : worldY),
    [flipView],
  )

  const paint = useCallback(() => {
    const ball = ballRef.current
    const ballEl = ballElRef.current
    if (ballEl) {
      ballEl.style.left = `${ball.x * 100}%`
      ballEl.style.top = `${viewY(ball.y) * 100}%`
    }
    const myEl = myPaddleElRef.current
    if (myEl) myEl.style.left = `${myPaddleXRef.current * 100}%`
    const peerEl = peerPaddleElRef.current
    if (peerEl) peerEl.style.left = `${peerPaddleXRef.current * 100}%`
  }, [viewY, ballRef, ballElRef, myPaddleElRef, peerPaddleElRef, myPaddleXRef, peerPaddleXRef])

  const syncScoreDom = useCallback(() => {
    const el = scoreElRef.current
    if (!el) return
    const n = isOnline ? (isGuest ? guestScoreRef.current : hostScoreRef.current) : soloScoreRef.current
    el.textContent = String(n)
  }, [isGuest, isOnline, scoreElRef, hostScoreRef, guestScoreRef, soloScoreRef])

  return { viewY, paint, syncScoreDom }
}

/**
 * Guest-клиент: экстраполяция позиции мяча по velocity между пакетами WS
 * (~50 Гц → визуально 60), с lerp-сглаживанием ракетки хоста.
 */
export function useEmojiCatchGuestTick({
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
}: {
  isGuest: boolean
  finished: boolean
  netRef: NetRef
  paint: () => void
  roundId: number
  ballRef: MutableRefObject<BallState>
  peerPaddleXRef: MutableRefObject<number>
  lastTsRef: MutableRefObject<number | null>
  rafRef: MutableRefObject<number>
  finishedRef: MutableRefObject<boolean>
}) {
  useEffect(() => {
    if (!isGuest || finished || !netRef) return
    lastTsRef.current = null

    const tick = (ts: number) => {
      if (finishedRef.current) return
      const prev = lastTsRef.current ?? ts
      lastTsRef.current = ts
      const dt = Math.min(0.05, (ts - prev) / 1000)

      const snap = netRef.current.snapshot
      if (snap) {
        const ageSec = Math.min(GUEST_EXTRAPOLATE_MAX_SEC, (ts - snap.receivedAt) / 1000)
        ballRef.current = {
          x: snap.ball_x + snap.vx * ageSec,
          y: snap.ball_y + snap.vy * ageSec,
          vx: snap.vx,
          vy: snap.vy,
        }
        const targetPeer = snap.host_paddle_x
        peerPaddleXRef.current += (targetPeer - peerPaddleXRef.current) * PADDLE_LERP
        void dt
      }
      paint()
      rafRef.current = requestAnimationFrame(tick)
    }
    rafRef.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(rafRef.current)
  }, [finished, isGuest, netRef, paint, roundId, ballRef, peerPaddleXRef, lastTsRef, rafRef, finishedRef])
}

/**
 * Ввод ракетки: pointer-move (с cursor-lock), стрелки/WASD.
 */
export function useEmojiCatchInput({
  fieldRef,
  finished,
  roundId,
  finishedRef,
  movePaddleByDelta,
  movePaddleToClientX,
  applyMyPaddle,
  myPaddleXRef,
}: {
  fieldRef: MutableRefObject<HTMLDivElement | null>
  finished: boolean
  roundId: number
  finishedRef: MutableRefObject<boolean>
  movePaddleByDelta: (deltaClientX: number) => void
  movePaddleToClientX: (clientX: number) => void
  applyMyPaddle: (next: number) => void
  myPaddleXRef: MutableRefObject<number>
}) {
  useEffect(() => {
    if (finished) return
    const field = fieldRef.current
    const onMove = (e: PointerEvent) => {
      if (finishedRef.current) return
      if (document.pointerLockElement === field) {
        movePaddleByDelta(e.movementX)
        return
      }
      movePaddleToClientX(e.clientX)
    }
    document.addEventListener('pointermove', onMove, { passive: true })
    return () => document.removeEventListener('pointermove', onMove)
  }, [finished, movePaddleByDelta, movePaddleToClientX, fieldRef, finishedRef, roundId])

  useEffect(() => {
    if (finished) return
    const field = fieldRef.current
    if (!field) return
    document.body.classList.add('emoji-pong-cursor-lock')
    return () => {
      document.body.classList.remove('emoji-pong-cursor-lock')
      if (document.pointerLockElement === field) document.exitPointerLock?.()
    }
  }, [finished, fieldRef, roundId])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (finishedRef.current) return
      const step = 0.04
      const half = EMOJI_PONG_PADDLE_WIDTH_RATIO / 2
      if (e.key === 'ArrowLeft' || e.key === 'a' || e.key === 'A') {
        e.preventDefault()
        applyMyPaddle(Math.max(half, myPaddleXRef.current - step))
      } else if (e.key === 'ArrowRight' || e.key === 'd' || e.key === 'D') {
        e.preventDefault()
        applyMyPaddle(Math.min(1 - half, myPaddleXRef.current + step))
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [applyMyPaddle, myPaddleXRef, finishedRef])
}
