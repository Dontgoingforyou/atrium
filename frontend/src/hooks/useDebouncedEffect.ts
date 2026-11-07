import { useEffect, useRef } from 'react'

/** Вызов effect через delayMs после последнего изменения deps.
 *  Cleanup, возвращённый effect, вызывается перед следующим запуском и при unmount. */
export function useDebouncedEffect(
  effect: () => void | (() => void),
  deps: readonly unknown[],
  delayMs: number,
) {
  const effectRef = useRef(effect)
  effectRef.current = effect
  const cleanupRef = useRef<(() => void) | null>(null)

  useEffect(() => {
    const timer = setTimeout(() => {
      if (cleanupRef.current) {
        cleanupRef.current()
        cleanupRef.current = null
      }
      const next = effectRef.current()
      cleanupRef.current = typeof next === 'function' ? next : null
    }, delayMs)
    return () => {
      clearTimeout(timer)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- debounce по deps
  }, deps)

  useEffect(() => {
    return () => {
      if (cleanupRef.current) {
        cleanupRef.current()
        cleanupRef.current = null
      }
    }
  }, [])
}
