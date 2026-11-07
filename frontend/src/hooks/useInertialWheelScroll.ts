import { useEffect, useRef, type RefObject } from 'react'

export const INERTIAL_SCROLL_MAX_VELOCITY = 28
export const INERTIAL_SCROLL_FRICTION = 0.84
export const INERTIAL_SCROLL_STOP_THRESHOLD = 0.5
export const INERTIAL_SCROLL_WHEEL_DAMPING = 0.6
export const INERTIAL_SCROLL_IDLE_MS = 150

export function resolveHorizontalWheelDelta(deltaX: number, deltaY: number, shiftKey: boolean): number | null {
  if (shiftKey && deltaY !== 0) return deltaY
  if (deltaX !== 0 && Math.abs(deltaX) >= Math.abs(deltaY)) return deltaX
  return null
}

export function resolveDragBoardWheelDelta(deltaX: number, deltaY: number, shiftKey: boolean): number | null {
  const horizontal = resolveHorizontalWheelDelta(deltaX, deltaY, shiftKey)
  if (horizontal !== null) return horizontal
  if (deltaY !== 0) return deltaY
  return null
}

export function dampWheelDelta(delta: number, damping = INERTIAL_SCROLL_WHEEL_DAMPING): number {
  return delta * damping
}

export function clampVelocity(velocity: number, max: number): number {
  if (velocity > max) return max
  if (velocity < -max) return -max
  return velocity
}

export function applyFriction(velocity: number, friction: number, stopThreshold: number): number {
  const next = velocity * friction
  return Math.abs(next) < stopThreshold ? 0 : next
}

export function useInertialWheelScroll(scrollRef: RefObject<HTMLElement | null>, enabled = true): void {
  const velocityRef = useRef(0)
  const rafRef = useRef<number | null>(null)
  const idleTimerRef = useRef<number | null>(null)

  useEffect(() => {
    if (!enabled) return
    const el = scrollRef.current
    if (!el) return

    const stopLoop = () => {
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current)
        rafRef.current = null
      }
    }

    const clearIdleTimer = () => {
      if (idleTimerRef.current !== null) {
        window.clearTimeout(idleTimerRef.current)
        idleTimerRef.current = null
      }
    }

    const tick = () => {
      const current = scrollRef.current
      if (!current) {
        stopLoop()
        return
      }
      velocityRef.current = applyFriction(
        velocityRef.current,
        INERTIAL_SCROLL_FRICTION,
        INERTIAL_SCROLL_STOP_THRESHOLD,
      )
      if (velocityRef.current === 0) {
        rafRef.current = null
        return
      }
      current.scrollLeft += velocityRef.current
      rafRef.current = requestAnimationFrame(tick)
    }

    const onWheel = (e: WheelEvent) => {
      const rawDelta = resolveHorizontalWheelDelta(e.deltaX, e.deltaY, e.shiftKey)
      if (rawDelta === null) return
      e.preventDefault()
      const delta = dampWheelDelta(rawDelta)
      velocityRef.current = clampVelocity(velocityRef.current + delta, INERTIAL_SCROLL_MAX_VELOCITY)
      if (rafRef.current === null) {
        rafRef.current = requestAnimationFrame(tick)
      }
      clearIdleTimer()
      idleTimerRef.current = window.setTimeout(() => {
        velocityRef.current = 0
        stopLoop()
      }, INERTIAL_SCROLL_IDLE_MS)
    }

    el.addEventListener('wheel', onWheel, { passive: false })
    return () => {
      el.removeEventListener('wheel', onWheel)
      clearIdleTimer()
      stopLoop()
      velocityRef.current = 0
    }
  }, [scrollRef, enabled])
}
