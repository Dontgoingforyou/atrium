import { type MouseEvent, type RefObject, useCallback, useEffect, useState } from 'react'

import { useBodyScrollLock } from '../../hooks/useBodyScrollLock'
import { useFocusTrap } from '../../hooks/useFocusTrap'
import { useGuidedTourActive } from '../../hooks/useGuidedTourActive'
import { useNarrowViewport } from '../../hooks/useNarrowViewport'

const APP_NAV_ID = 'app-nav'

type AppNavDrawer = {
  navId: string
  narrow: boolean
  drawerOpen: boolean
  drawerModal: boolean
  toggle: () => void
  close: () => void
  onSidebarClick: (event: MouseEvent<HTMLElement>) => void
}

export function useAppNavDrawer(
  pathname: string,
  menuBtnRef: RefObject<HTMLButtonElement | null>,
  asideRef: RefObject<HTMLElement | null>,
): AppNavDrawer {
  const narrow = useNarrowViewport()
  const tour = useGuidedTourActive()
  const [requestedOpen, setRequestedOpen] = useState(false)
  const [trackedPath, setTrackedPath] = useState(pathname)
  const [trackedNarrow, setTrackedNarrow] = useState(narrow)

  if (trackedPath !== pathname) {
    setTrackedPath(pathname)
    setRequestedOpen(false)
  }
  if (trackedNarrow !== narrow) {
    setTrackedNarrow(narrow)
    if (!narrow) setRequestedOpen(false)
  }

  const drawerOpen = narrow && (tour || requestedOpen)
  const drawerModal = drawerOpen && !tour

  const close = useCallback(() => {
    setRequestedOpen(false)
    menuBtnRef.current?.focus()
  }, [menuBtnRef])

  const toggle = useCallback(() => {
    setRequestedOpen((open) => !open)
  }, [])

  useBodyScrollLock(drawerModal)
  useFocusTrap(asideRef, drawerModal)

  useEffect(() => {
    if (!drawerModal) return
    const aside = asideRef.current
    const first = aside?.querySelector<HTMLElement>('a[href], button:not([disabled])')
    first?.focus()
  }, [asideRef, drawerModal])

  useEffect(() => {
    if (!drawerModal) return
    function onKey(event: KeyboardEvent) {
      if (event.key !== 'Escape' || event.defaultPrevented) return
      const dialogs = document.querySelectorAll('[role="dialog"][aria-modal="true"]')
      const top = dialogs[dialogs.length - 1]
      if (top && top !== asideRef.current) return
      event.preventDefault()
      setRequestedOpen(false)
      menuBtnRef.current?.focus()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [asideRef, drawerModal, menuBtnRef])

  const onSidebarClick = useCallback((event: MouseEvent<HTMLElement>) => {
    const target = event.target
    if (!(target instanceof Element)) return
    if (target.closest('a')) setRequestedOpen(false)
  }, [])

  return {
    navId: APP_NAV_ID,
    narrow,
    drawerOpen,
    drawerModal,
    toggle,
    close,
    onSidebarClick,
  }
}
