/** Синхронная защита от двойного submit (Enter + form, гонка до setState). */
export function tryAcquireMessageSubmitLock(inFlight: { current: boolean }): boolean {
  if (inFlight.current) return false
  inFlight.current = true
  return true
}

export function releaseMessageSubmitLock(inFlight: { current: boolean }): void {
  inFlight.current = false
}
