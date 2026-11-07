import { useEffect, useRef, useState } from 'react'

const DEFAULT_DURATION_MS = 480

function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined') return false
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function easeOutCubic(t: number): number {
  return 1 - (1 - t) ** 3
}

/** Плавный переход числа (для диаграмм и счётчиков). */
export function useAnimatedNumber(target: number, durationMs = DEFAULT_DURATION_MS): number {
  const [value, setValue] = useState(target)
  const currentRef = useRef(target)

  useEffect(() => {
    if (prefersReducedMotion()) {
      currentRef.current = target
      const id = requestAnimationFrame(() => setValue(target))
      return () => cancelAnimationFrame(id)
    }

    const from = currentRef.current
    if (from === target) return

    let frameId = 0
    const start = performance.now()

    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / durationMs)
      const next = from + (target - from) * easeOutCubic(t)
      currentRef.current = next
      setValue(next)
      if (t < 1) {
        frameId = requestAnimationFrame(tick)
      } else {
        currentRef.current = target
        setValue(target)
      }
    }

    frameId = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frameId)
  }, [target, durationMs])

  return value
}

export function useAnimatedInteger(target: number, durationMs = DEFAULT_DURATION_MS): number {
  return Math.round(useAnimatedNumber(target, durationMs))
}
