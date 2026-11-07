import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useQueryClient } from '@tanstack/react-query'
import { useLocation, useNavigate } from 'react-router'

import { useAuthStore } from '../store/authStore'
import { useNotifyToast } from '../hooks/useNotifyToast'
import { dispatchGuidedTourCloseCtx } from './ensureTourDemoChat'
import { cleanupGuidedTourDemoTask } from './ensureTourDemoTask'
import {
  cleanupGuidedTourDemoSpecialist,
  resolveTourDemoSpecialistCleanup,
} from './ensureTourDemoSpecialist'
import { cleanupGuidedTourDemoEvent } from './ensureTourDemoEvent'
import {
  cleanupGuidedTourDemoTimeEntries,
} from './ensureTourDemoTimeEntry'
import { cleanupGuidedTourDemoDocument } from './ensureTourDemoDocument'
import { fitPopoverAwayFromTarget } from '../utils/guidedTourLayout'
import {
  resolveGuidedTourHintDismissLabel,
} from '../domain/onboarding/guidedTour'
import { tourLocationKey } from '../domain/onboarding/guidedTourPages'
import {
  clearTourReveal,
  computePopoverPos,
  prefersReducedMotion,
  readRect,
} from './tourEngineHelpers'
import { persistHintPageSeen, persistLinearTourSeen } from './persistTourSeen'
import { prepareTourStep } from './prepareTourStep'
import { TourDoneModal } from './TourDoneModal'
import { TourPopover } from './TourPopover'
import { TourSpotlight, type SpotlightRect } from './TourSpotlight'
import { TourWelcomeModal } from './TourWelcomeModal'
import { useTourStore } from './tourStore'
import {
  PORTAL_TIME_ENTRIES_REPORT_ROOT_QUERY_KEY,
  PORTAL_TIME_ENTRIES_ROOT_QUERY_KEY,
  PORTAL_TIME_ENTRIES_SUMMARY_ROOT_QUERY_KEY,
} from '@/api/queryKeys'
import { SPECIALISTS_DETAIL_ROOT_QUERY_KEY, SPECIALISTS_LIST_QUERY_KEY } from '@/pages/specialists/specialistQueryKeys'
import styles from '@/styles/modules/onboarding/GuidedTour.module.css'

type Props = {
  onComplete: () => void
  canSkipEntire: boolean
  tourVariant?: 'full' | 'timesheet'
}

export function TourEngine({ onComplete, canSkipEntire, tourVariant = 'full' }: Props) {
  const navigate = useNavigate()
  const location = useLocation()
  const qc = useQueryClient()
  const currentUserSub = useAuthStore((s) => s.user?.sub)
  const phase = useTourStore((s) => s.phase)
  const mode = useTourStore((s) => s.mode)
  const stepIndex = useTourStore((s) => s.stepIndex)
  const steps = useTourStore((s) => s.steps)
  const hasEnteredRunning = useTourStore((s) => s.hasEnteredRunning)
  const startRunning = useTourStore((s) => s.startRunning)
  const openDone = useTourStore((s) => s.openDone)
  const resetIdle = useTourStore((s) => s.resetIdle)
  const setHintFrozenLocationKeys = useTourStore((s) => s.setHintFrozenLocationKeys)
  const next = useTourStore((s) => s.next)
  const back = useTourStore((s) => s.back)
  const skipMissing = useTourStore((s) => s.skipMissing)
  const setDemoTask = useTourStore((s) => s.setDemoTask)
  const setDemoSpecialist = useTourStore((s) => s.setDemoSpecialist)
  const setDemoEvent = useTourStore((s) => s.setDemoEvent)
  const setDemoChat = useTourStore((s) => s.setDemoChat)
  const setDemoTimeEntries = useTourStore((s) => s.setDemoTimeEntries)
  const setDemoDocument = useTourStore((s) => s.setDemoDocument)
  const notify = useNotifyToast()

  const step = phase === 'running' ? steps[stepIndex] : undefined
  const [rect, setRect] = useState<SpotlightRect | null>(null)
  const [popoverVisible, setPopoverVisible] = useState(false)
  const [displayStepIndex, setDisplayStepIndex] = useState(0)
  const genRef = useRef(0)
  const prevStepIndexRef = useRef(stepIndex)
  const hintFinishingRef = useRef(false)
  const popoverRef = useRef<HTMLDivElement>(null)
  const [fittedPos, setFittedPos] = useState<{ top: number; left: number } | null>(null)
  const popoverPos = computePopoverPos(rect, step?.preferPlacement)

  useEffect(() => {
    if (phase === 'running') {
      document.documentElement.setAttribute('data-guided-tour', '1')
    } else {
      document.documentElement.removeAttribute('data-guided-tour')
      clearTourReveal()
    }
    return () => {
      document.documentElement.removeAttribute('data-guided-tour')
      clearTourReveal()
    }
  }, [phase])

  useEffect(() => {
    if (phase !== 'running' || !step) return
    const current = step
    const currentIndex = stepIndex
    const missingTargetPolicy = stepIndex < prevStepIndexRef.current ? 'keep' : 'skip'
    prevStepIndexRef.current = stepIndex
    const gen = ++genRef.current
    let cancelled = false

    void (async () => {
      clearTourReveal()
      dispatchGuidedTourCloseCtx()
      await prepareTourStep({
        current,
        currentIndex,
        isStale: () => cancelled || gen !== genRef.current,
        reduced: prefersReducedMotion(),
        pathname: location.pathname,
        search: location.search,
        locationState: location.state,
        currentUserSub,
        navigate,
        qc,
        skipMissing,
        missingTargetPolicy,
        setDemoTask,
        setDemoSpecialist,
        setDemoEvent,
        setDemoChat,
        setDemoTimeEntries,
        setDemoDocument,
        ui: { setPopoverVisible, setRect, setDisplayStepIndex },
        notify,
      })
    })()

    return () => {
      cancelled = true
    }
  }, [
    phase,
    step,
    stepIndex,
    location.pathname,
    location.search,
    location.state,
    navigate,
    skipMissing,
    currentUserSub,
    qc,
    setDemoTask,
    setDemoSpecialist,
    setDemoEvent,
    setDemoChat,
    setDemoTimeEntries,
    setDemoDocument,
    notify,
  ])

  const stepReady = popoverVisible && displayStepIndex === stepIndex

  useEffect(() => {
    if (!step?.selector || !stepReady) return
    const selector = step.selector
    let raf = 0
    function sync() {
      if (raf) return
      raf = window.requestAnimationFrame(() => {
        raf = 0
        const el = document.querySelector(selector)
        if (el) setRect(readRect(el))
      })
    }
    window.addEventListener('resize', sync)
    window.addEventListener('scroll', sync, true)
    return () => {
      window.removeEventListener('resize', sync)
      window.removeEventListener('scroll', sync, true)
      if (raf) window.cancelAnimationFrame(raf)
    }
  }, [stepReady, step])

  const cleanupTourDemosThen = useCallback(async (finish: () => void) => {
    dispatchGuidedTourCloseCtx()
    const state = useTourStore.getState()
    if (state.demoTaskId) {
      await cleanupGuidedTourDemoTask(state.demoTaskId)
      setDemoTask(null, null)
      await qc.invalidateQueries({ queryKey: ['portal', 'tasks'] })
    }
    const specialistToRemove = resolveTourDemoSpecialistCleanup({
      demoSpecialistSub: state.demoSpecialistSub,
      demoSpecialistCreated: state.demoSpecialistCreated,
      currentUserSub,
    })
    if (specialistToRemove) {
      await cleanupGuidedTourDemoSpecialist(specialistToRemove, currentUserSub)
      setDemoSpecialist(null, false)
      await qc.invalidateQueries({ queryKey: SPECIALISTS_LIST_QUERY_KEY })
      await qc.invalidateQueries({ queryKey: SPECIALISTS_DETAIL_ROOT_QUERY_KEY })
    }
    if (state.demoEventId) {
      await cleanupGuidedTourDemoEvent(state.demoEventId)
      setDemoEvent(null)
      await qc.invalidateQueries({ queryKey: ['portal', 'calendar'] })
    }
    if (state.demoTimeEntryIds.length > 0) {
      await cleanupGuidedTourDemoTimeEntries(state.demoTimeEntryIds)
      setDemoTimeEntries([])
      await qc.invalidateQueries({ queryKey: PORTAL_TIME_ENTRIES_ROOT_QUERY_KEY })
      await qc.invalidateQueries({ queryKey: PORTAL_TIME_ENTRIES_SUMMARY_ROOT_QUERY_KEY })
      await qc.invalidateQueries({ queryKey: PORTAL_TIME_ENTRIES_REPORT_ROOT_QUERY_KEY })
    }
    if (state.demoDocumentId) {
      await cleanupGuidedTourDemoDocument()
      setDemoDocument(null, false)
      await qc.invalidateQueries({ queryKey: ['portal', 'navigation-tree'] })
    }
    finish()
  }, [
    qc,
    currentUserSub,
    setDemoTask,
    setDemoSpecialist,
    setDemoEvent,
    setDemoTimeEntries,
    setDemoDocument,
  ])

  const finishHintPage = useCallback(() => {
    if (hintFinishingRef.current) return
    hintFinishingRef.current = true
    persistHintPageSeen(currentUserSub, steps)
    void cleanupTourDemosThen(() => {
      resetIdle()
    })
  }, [cleanupTourDemosThen, currentUserSub, resetIdle, steps])

  useEffect(() => {
    if (phase !== 'running' || !stepReady) return
    const isLastStep = stepIndex >= steps.length - 1
    const canGoBack = stepIndex > 0

    function onKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        e.preventDefault()
        e.stopPropagation()
        if (mode === 'hint') finishHintPage()
        else if (canSkipEntire || isLastStep) openDone()
        else next()
        return
      }
      if (e.key !== 'ArrowRight' && e.key !== 'ArrowDown' && e.key !== 'ArrowLeft' && e.key !== 'ArrowUp') {
        return
      }
      e.preventDefault()
      e.stopPropagation()
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
        if (isLastStep) openDone()
        else next()
      } else if (canGoBack) {
        back()
      }
    }

    window.addEventListener('keydown', onKeyDown, true)
    return () => window.removeEventListener('keydown', onKeyDown, true)
  }, [
    phase,
    stepReady,
    stepIndex,
    steps.length,
    next,
    back,
    openDone,
    canSkipEntire,
    mode,
    finishHintPage,
  ])

  useLayoutEffect(() => {
    if (!stepReady || !popoverRef.current || typeof window === 'undefined') {
      return
    }
    const el = popoverRef.current
    const target = rect
      ? {
          ...rect,
          bottom: rect.top + rect.height,
          right: rect.left + rect.width,
        }
      : null

    function applyFit() {
      const box = el.getBoundingClientRect()
      const next = fitPopoverAwayFromTarget(
        popoverPos,
        { width: box.width, height: box.height },
        { width: window.innerWidth, height: window.innerHeight },
        target,
      )
      setFittedPos((prev) => {
        if (prev && prev.top === next.top && prev.left === next.left) return prev
        return next
      })
    }

    const ro = new ResizeObserver(() => {
      applyFit()
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [stepReady, popoverPos, displayStepIndex, rect])

  useEffect(() => {
    if (mode === 'hint' && phase === 'running') {
      hintFinishingRef.current = false
    }
  }, [mode, phase])

  useEffect(() => {
    if (phase === 'done' && mode === 'hint') {
      finishHintPage()
    }
  }, [phase, mode, finishHintPage])

  function finishAndPersist() {
    persistLinearTourSeen({
      userSub: currentUserSub,
      steps,
      stepIndex,
      hasEnteredRunning,
    })
    const dest = tourVariant === 'timesheet' ? '/analytics/timesheets' : '/'
    setHintFrozenLocationKeys([
      tourLocationKey(location.pathname, location.search),
      dest,
    ])
    void cleanupTourDemosThen(() => {
      resetIdle()
      onComplete()
      navigate(dest)
    })
  }

  if (phase === 'idle') return null

  if (phase === 'done' && mode === 'hint') {
    return null
  }

  if (phase === 'welcome') {
    return createPortal(
      <TourWelcomeModal
        onStart={() => startRunning()}
        canSkipEntire={canSkipEntire}
        onSkip={canSkipEntire ? () => openDone() : undefined}
        variant={tourVariant}
      />,
      document.body,
    )
  }

  if (phase === 'done') {
    return createPortal(<TourDoneModal onFinish={finishAndPersist} variant={tourVariant} />, document.body)
  }

  if (!step) {
    return createPortal(
      <div className={`${styles.overlayRoot} ${styles.overlayRootInteractive}`} aria-busy="true">
        <TourSpotlight rect={null} />
      </div>,
      document.body,
    )
  }

  const total = steps.length
  const progressLabel = `${stepIndex + 1} из ${total}`
  const isLast = stepIndex >= total - 1
  const canBack = stepIndex > 0

  function skipTourOrStep() {
    if (mode === 'hint') {
      finishHintPage()
      return
    }
    if (canSkipEntire) {
      openDone()
      return
    }
    if (isLast) openDone()
    else next()
  }

  return createPortal(
    <div className={`${styles.overlayRoot} ${styles.overlayRootInteractive}`}>
      <TourSpotlight rect={stepReady ? rect : null} />
      <TourPopover
        ref={popoverRef}
        title={step.title}
        body={step.body}
        progressLabel={progressLabel}
        style={stepReady ? (fittedPos ?? popoverPos) : popoverPos}
        contentKey={step.id}
        visible={stepReady}
        canBack={canBack}
        onBack={back}
        onNext={() => {
          if (isLast) {
            if (mode === 'hint') finishHintPage()
            else openDone()
          } else next()
        }}
        onSkip={skipTourOrStep}
        showSkip
        canSkipEntire={mode === 'hint' ? false : canSkipEntire}
        skipLabel={mode === 'hint' ? resolveGuidedTourHintDismissLabel() : undefined}
        isLast={isLast}
      />
    </div>,
    document.body,
  )
}
