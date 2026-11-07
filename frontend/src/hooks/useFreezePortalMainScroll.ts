import { useLayoutEffect, type RefObject } from 'react'

export function useFreezePortalMainScroll(
  active: boolean,
  lockedTopRef: RefObject<number | null>,
): void {
  useLayoutEffect(() => {
    if (!active) return
    const main = document.querySelector('[data-portal-main]')
    if (!(main instanceof HTMLElement)) return

    const locked = lockedTopRef.current ?? main.scrollTop
    lockedTopRef.current = locked
    if (main.scrollTop !== locked) {
      main.scrollTop = locked
    }

    const onScroll = () => {
      if (main.scrollTop !== locked) {
        main.scrollTop = locked
      }
    }

    main.addEventListener('scroll', onScroll)
    return () => {
      main.removeEventListener('scroll', onScroll)
    }
  }, [active, lockedTopRef])
}

export function capturePortalMainScrollTop(lockedTopRef: { current: number | null }): void {
  const main = document.querySelector('[data-portal-main]')
  if (main instanceof HTMLElement) {
    lockedTopRef.current = main.scrollTop
  }
}

export function clearPortalMainScrollLock(lockedTopRef: { current: number | null }): void {
  lockedTopRef.current = null
}
