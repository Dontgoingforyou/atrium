import type { QueryClient } from '@tanstack/react-query'
import type { NavigateFunction } from 'react-router'

import { PORTAL_CHATS_ALL_QUERY_KEY } from '../api/queryKeys'
import {
  PORTAL_TIME_ENTRIES_REPORT_ROOT_QUERY_KEY,
  PORTAL_TIME_ENTRIES_ROOT_QUERY_KEY,
  PORTAL_TIME_ENTRIES_SUMMARY_ROOT_QUERY_KEY,
} from '../api/queryKeys'
import { SPECIALISTS_DETAIL_ROOT_QUERY_KEY, SPECIALISTS_LIST_QUERY_KEY } from '../pages/specialists/specialistQueryKeys'
import { scrollTourAnchorIntoView, waitForTourTarget } from '../utils/guidedTourLayout'
import {
  resolveTourStepNavigationKind,
  stepNeedsTourCreateFormPage,
  stepNeedsTourDocument,
  stepNeedsTourTaskDetailPage,
  tourTaskDetailAnchorForStep,
  type GuidedTourStepDef,
} from '../domain/onboarding/guidedTour'
import {
  dispatchGuidedTourOpenCtx,
  stepNeedsTourChatHref,
  stepNeedsTourChatRow,
  stepNeedsTourChatSeed,
  waitForTourChatMessageAnchor,
} from './ensureTourDemoChat'
import {
  dispatchGuidedTourTaskPanel,
  stepNeedsTourDemoTask,
  type TourDemoTaskPrefill,
} from './ensureTourDemoTask'
import { stepNeedsTourDemoSpecialist } from './ensureTourDemoSpecialist'
import { stepNeedsTourDemoEvent, calendarTourEventHref, calendarTourEventLocationMatches } from './ensureTourDemoEvent'
import { stepNeedsTourDemoTimeEntry } from './ensureTourDemoTimeEntry'
import { stepNeedsTourDemoDocument } from './ensureTourDemoDocument'
import {
  AFTER_SCROLL_MS,
  applyTourReveal,
  locationMatchesHref,
  POPOVER_FADE_MS,
  readRect,
  resolveTourOpenHref,
  routeMatches,
  sleep,
} from './tourEngineHelpers'
import {
  ensureChatRowForStep,
  ensureDemoDocumentForStep,
  ensureDemoEventForStep,
  ensureDemoSpecialistForStep,
  ensureDemoTaskForStep,
  ensureDemoTimeEntriesForStep,
  type TourNotify,
} from './tourPrepareDemos'
import { useTourStore } from './tourStore'
import type { SpotlightRect } from './TourSpotlight'

/** Дольше обычного: scrollIntoView({ block: 'center' }) на учебных якорях чата и последнем шаге. */
const AFTER_CENTER_SCROLL_MS = 180

const EXTRA_WAIT_ANCHOR: Record<string, string> = {
  'specialists-kanban-card': '[data-tour="specialists-kanban-card"]',
  'specialists-detail': '[data-tour="specialists-detail"]',
  'calendar-event': '[data-tour="calendar-event"]',
  'calendar-event-detail': '[data-tour="calendar-event-detail"]',
  'calendar-event-edit-form': '[data-tour="calendar-event-edit-form"]',
  'timesheets-report': '[data-tour="timesheets-report-table"]',
  'document-body': '[data-tour="document-body"]',
  'tasks-detail-subtasks': '[data-tour="task-detail-subtasks"]',
  'tasks-detail-comments': '[data-tour="task-detail-comments"]',
  'tasks-detail-links': '[data-tour="task-detail-links"]',
  'tasks-detail-files': '[data-tour="task-detail-files"]',
}

type PrepareUi = {
  setPopoverVisible: (v: boolean) => void
  setRect: (r: SpotlightRect | null) => void
  setDisplayStepIndex: (i: number) => void
}

export type PrepareTourStepArgs = {
  current: GuidedTourStepDef
  currentIndex: number
  isStale: () => boolean
  reduced: boolean
  pathname: string
  search: string
  locationState: unknown
  currentUserSub: string | undefined
  navigate: NavigateFunction
  qc: QueryClient
  skipMissing: () => void
  /** При «Назад» не продвигать тур вперёд, если якорь не найден. */
  missingTargetPolicy: 'skip' | 'keep'
  setDemoTask: (taskId: string | null, prefill: TourDemoTaskPrefill | null) => void
  setDemoSpecialist: (specialistSub: string | null, created: boolean) => void
  setDemoEvent: (eventId: string | null) => void
  setDemoChat: (chatId: string | null) => void
  setDemoTimeEntries: (entryIds: string[]) => void
  setDemoDocument: (documentId: string | null, created: boolean) => void
  ui: PrepareUi
  notify: TourNotify
}

function showPopoverWithoutTarget(ui: PrepareUi, currentIndex: number): void {
  ui.setRect(null)
  ui.setDisplayStepIndex(currentIndex)
  ui.setPopoverVisible(true)
}

function tourAnchorScrollBlock(stepId: string): ScrollLogicalPosition {
  if (stepId === 'account-restart') {
    return 'end'
  }
  if (stepId === 'chats-messages' || stepId === 'chats-emoji-easter') {
    return 'center'
  }
  return 'nearest'
}

function hideAndNavigate(ui: PrepareUi, navigate: NavigateFunction, to: string, state?: object): void {
  ui.setPopoverVisible(false)
  ui.setRect(null)
  navigate(to, state ? { state } : undefined)
}

/** Подготовка якоря шага тура: демо-сущности, навигация, spotlight. */
export async function prepareTourStep(args: PrepareTourStepArgs): Promise<void> {
  const {
    current,
    currentIndex,
    isStale,
    reduced,
    pathname,
    search,
    locationState,
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
    ui,
    notify,
  } = args

  if (stepNeedsTourDemoTimeEntry(current)) {
    const timeReady = await ensureDemoTimeEntriesForStep(
      current,
      setDemoTimeEntries,
      async () => {
        await qc.invalidateQueries({ queryKey: PORTAL_TIME_ENTRIES_ROOT_QUERY_KEY })
        await qc.invalidateQueries({ queryKey: PORTAL_TIME_ENTRIES_SUMMARY_ROOT_QUERY_KEY })
        await qc.invalidateQueries({ queryKey: PORTAL_TIME_ENTRIES_REPORT_ROOT_QUERY_KEY })
      },
      notify,
    )
    if (isStale()) return
    if (timeReady.status === 'failed') {
      showPopoverWithoutTarget(ui, currentIndex)
      return
    }
    if (current.id === 'timesheets-entries' && new URLSearchParams(search).get('tab') === 'report') {
      hideAndNavigate(ui, navigate, '/analytics/timesheets')
      return
    }
    const needsNav = Boolean(current.route) && !routeMatches(pathname, search, current.route)
    if (needsNav) {
      hideAndNavigate(ui, navigate, current.route!)
      return
    }
  } else if (stepNeedsTourDemoDocument(current)) {
    const docReady = await ensureDemoDocumentForStep(
      current,
      setDemoDocument,
      async () => {
        await qc.invalidateQueries({ queryKey: ['portal', 'navigation-tree'] })
      },
      notify,
    )
    if (isStale()) return
    if (docReady.status === 'failed') {
      showPopoverWithoutTarget(ui, currentIndex)
      return
    }
    const demoDocId = docReady.documentId ?? useTourStore.getState().demoDocumentId
    if (demoDocId && stepNeedsTourDocument(current)) {
      const docHref = `/documents/${encodeURIComponent(demoDocId)}`
      if (!locationMatchesHref(pathname, search, docHref)) {
        hideAndNavigate(ui, navigate, docHref)
        return
      }
    } else {
      const needsNav = Boolean(current.route) && !routeMatches(pathname, search, current.route)
      if (needsNav) {
        hideAndNavigate(ui, navigate, current.route!)
        return
      }
    }
  } else if (stepNeedsTourDemoTask(current)) {
    const taskReady = await ensureDemoTaskForStep(
      current,
      currentUserSub,
      setDemoTask,
      async () => {
        await qc.invalidateQueries({ queryKey: ['portal', 'tasks'] })
      },
      notify,
    )
    if (isStale()) return
    if (taskReady.status === 'failed') {
      showPopoverWithoutTarget(ui, currentIndex)
      return
    }
    if (stepNeedsTourCreateFormPage(current)) {
      const prefill = useTourStore.getState().demoTaskPrefill
      const onNewPage = pathname === '/tasks/new'
      const hasPrefillState =
        Boolean((locationState as { tourDemo?: unknown } | null)?.tourDemo) || Boolean(prefill)
      if (!onNewPage || !hasPrefillState) {
        hideAndNavigate(ui, navigate, '/tasks/new', {
          tourDemo: prefill,
          initialAssigneeSubs: prefill?.assigneeSubs,
          initialStatus: 'todo',
        })
        return
      }
    } else if (stepNeedsTourTaskDetailPage(current)) {
      const demoTaskId = useTourStore.getState().demoTaskId
      if (!demoTaskId) {
        showPopoverWithoutTarget(ui, currentIndex)
        return
      }
      const detailHref = `/tasks/${encodeURIComponent(demoTaskId)}`
      if (!locationMatchesHref(pathname, search, detailHref)) {
        hideAndNavigate(ui, navigate, detailHref)
        return
      }
      const panelAnchor = tourTaskDetailAnchorForStep(current.id)
      if (panelAnchor) {
        dispatchGuidedTourTaskPanel(panelAnchor)
      }
    } else {
      const needsNav = Boolean(current.route) && !routeMatches(pathname, search, current.route)
      if (needsNav) {
        hideAndNavigate(ui, navigate, current.route!)
        return
      }
    }
  } else if (stepNeedsTourDemoSpecialist(current)) {
    const needsNav = Boolean(current.route) && !routeMatches(pathname, search, current.route)
    if (needsNav && current.id !== 'specialists-detail') {
      hideAndNavigate(ui, navigate, current.route!)
      return
    }
    const specialistReady = await ensureDemoSpecialistForStep(
      current,
      currentUserSub,
      setDemoSpecialist,
      async () => {
        await qc.invalidateQueries({ queryKey: SPECIALISTS_LIST_QUERY_KEY })
        await qc.invalidateQueries({ queryKey: SPECIALISTS_DETAIL_ROOT_QUERY_KEY })
      },
      notify,
    )
    if (isStale()) return
    if (specialistReady.status === 'failed') {
      showPopoverWithoutTarget(ui, currentIndex)
      return
    }
    const demoSub = useTourStore.getState().demoSpecialistSub
    if (current.id === 'specialists-detail') {
      if (!demoSub) {
        showPopoverWithoutTarget(ui, currentIndex)
        return
      }
      const detailHref = `/specialists?view=kanban&sub=${encodeURIComponent(demoSub)}`
      if (!locationMatchesHref(pathname, search, detailHref)) {
        hideAndNavigate(ui, navigate, detailHref)
        return
      }
    } else {
      const hasSub = new URLSearchParams(search.startsWith('?') ? search.slice(1) : search).get('sub')
      if (hasSub) {
        hideAndNavigate(ui, navigate, current.route ?? '/specialists?view=kanban')
        return
      }
    }
  } else if (stepNeedsTourDemoEvent(current)) {
    const needsNav = Boolean(current.route) && !routeMatches(pathname, search, current.route)
    const opensEventModal =
      current.id === 'calendar-event-detail' || current.id === 'calendar-event-edit-form'
    if (needsNav && !opensEventModal) {
      hideAndNavigate(ui, navigate, current.route!)
      return
    }
    const eventReady = await ensureDemoEventForStep(
      current,
      currentUserSub,
      setDemoEvent,
      async () => {
        await qc.invalidateQueries({ queryKey: ['portal', 'calendar'] })
      },
      notify,
    )
    if (isStale()) return
    if (eventReady.status === 'failed') {
      showPopoverWithoutTarget(ui, currentIndex)
      return
    }
    const demoEventId = useTourStore.getState().demoEventId
    if (current.id === 'calendar-event-detail' || current.id === 'calendar-event-edit-form') {
      if (!demoEventId) {
        showPopoverWithoutTarget(ui, currentIndex)
        return
      }
      const wantEdit = current.id === 'calendar-event-edit-form'
      const href = calendarTourEventHref(demoEventId, wantEdit)
      if (!calendarTourEventLocationMatches(pathname, search, demoEventId, wantEdit)) {
        hideAndNavigate(ui, navigate, href)
        return
      }
    } else {
      const params = new URLSearchParams(search.startsWith('?') ? search.slice(1) : search)
      if (params.get('event') || params.get('edit')) {
        hideAndNavigate(ui, navigate, current.route ?? '/calendar')
        return
      }
      if (needsNav) {
        hideAndNavigate(ui, navigate, current.route!)
        return
      }
    }
  } else {
    const needsNav = Boolean(current.route) && !routeMatches(pathname, search, current.route)
    if (needsNav) {
      hideAndNavigate(ui, navigate, current.route!)
      return
    }
  }

  let demoChatId: string | null = useTourStore.getState().demoChatId
  if (stepNeedsTourChatSeed(current)) {
    const earlySeed = current.id === 'chats-sidebar' || current.id === 'chats-new'
    const seedWork = ensureChatRowForStep(current, currentUserSub, setDemoChat, async (chatId) => {
      await qc.invalidateQueries({ queryKey: PORTAL_CHATS_ALL_QUERY_KEY })
      await qc.invalidateQueries({ queryKey: ['portal', 'messages', chatId] })
    }, notify)
    if (earlySeed && !demoChatId) {
      void seedWork.then((ready) => {
        if (ready.status === 'ok' && ready.chatId) setDemoChat(ready.chatId)
      })
    } else {
      const chatReady = await seedWork
      if (isStale()) return
      if (chatReady.status === 'failed') {
        showPopoverWithoutTarget(ui, currentIndex)
        return
      }
      demoChatId = chatReady.chatId || demoChatId
    }
  }

  const navigationKind = resolveTourStepNavigationKind({
    hasDemoChatId: Boolean(demoChatId),
    needsChatHref: stepNeedsTourChatHref(current),
    hasOpenFromSelector: Boolean(current.openFromSelector) && !useTourStore.getState().demoDocumentId,
  })
  if (navigationKind === 'demo-chat' && demoChatId) {
    const demoHref = `/chats?chat=${encodeURIComponent(demoChatId)}`
    if (!locationMatchesHref(pathname, search, demoHref)) {
      hideAndNavigate(ui, navigate, demoHref)
      return
    }
  } else if (navigationKind === 'open-from-selector' && current.openFromSelector) {
    const openEl = await waitForTourTarget(current.openFromSelector, 4000, 40)
    if (isStale()) return
    const openHref = openEl ? resolveTourOpenHref(openEl) : null
    if (!openHref) {
      if (missingTargetPolicy === 'keep' || stepNeedsTourDocument(current)) {
        showPopoverWithoutTarget(ui, currentIndex)
        return
      }
      skipMissing()
      return
    }
    if (!locationMatchesHref(pathname, search, openHref)) {
      hideAndNavigate(ui, navigate, openHref)
      return
    }
  }

  if (!reduced) await sleep(POPOVER_FADE_MS)
  if (isStale()) return

  if (!current.selector) {
    showPopoverWithoutTarget(ui, currentIndex)
    return
  }

  if (current.id === 'chats-messages') {
    await waitForTourChatMessageAnchor('text', '[data-tour="chats-message-row"]')
  }
  if (current.id === 'chats-emoji-easter') {
    await waitForTourChatMessageAnchor('emoji', '[data-tour="chats-emoji-easter"]')
  }
  const detailPanelAnchor = tourTaskDetailAnchorForStep(current.id)
  if (detailPanelAnchor) {
    dispatchGuidedTourTaskPanel(detailPanelAnchor)
  }
  const extraWaitSelector = current.id ? EXTRA_WAIT_ANCHOR[current.id] : undefined
  if (extraWaitSelector) {
    await waitForTourTarget(extraWaitSelector, 5000, 80)
  }

  const el = await waitForTourTarget(current.selector, 4000, 40)
  if (isStale()) return
  if (!el) {
    if (
      missingTargetPolicy === 'keep' ||
      stepNeedsTourDocument(current) ||
      stepNeedsTourDemoTimeEntry(current) ||
      stepNeedsTourDemoDocument(current) ||
      stepNeedsTourChatRow(current) ||
      stepNeedsTourDemoTask(current) ||
      stepNeedsTourDemoSpecialist(current) ||
      stepNeedsTourDemoEvent(current)
    ) {
      showPopoverWithoutTarget(ui, currentIndex)
      return
    }
    skipMissing()
    return
  }

  if (current.revealHover) {
    applyTourReveal(el)
  }

  const scrollBlock = tourAnchorScrollBlock(current.id)
  const useSmooth = !reduced && current.id !== 'account-restart' && scrollBlock !== 'end'
  scrollTourAnchorIntoView(el, { block: scrollBlock, smooth: useSmooth })
  if (!reduced) await sleep(scrollBlock === 'center' ? AFTER_CENTER_SCROLL_MS : AFTER_SCROLL_MS)
  if (isStale()) return

  if (current.id === 'chats-messages') {
    dispatchGuidedTourOpenCtx('message')
  } else if (current.id === 'chats-row') {
    dispatchGuidedTourOpenCtx('chat-row')
  }

  ui.setDisplayStepIndex(currentIndex)
  ui.setRect(readRect(el))
  ui.setPopoverVisible(true)
}
