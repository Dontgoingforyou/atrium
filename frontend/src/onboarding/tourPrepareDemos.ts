import { userFacingMessageFromUnknown } from '../utils/apiUserMessage'
import { waitForTourTarget } from '../utils/guidedTourLayout'
import type { GuidedTourStepDef } from '../domain/onboarding/guidedTour'
import {
  ensureGuidedTourDemoChat,
  stepNeedsTourChatSeed,
  waitForTourChatRow,
} from './ensureTourDemoChat'
import { useTourStore } from './tourStore'
import {
  ensureGuidedTourDemoTask,
  stepNeedsTourDemoTask,
  type TourDemoTaskPrefill,
} from './ensureTourDemoTask'
import {
  ensureGuidedTourDemoSpecialist,
  stepNeedsTourDemoSpecialist,
} from './ensureTourDemoSpecialist'
import {
  ensureGuidedTourDemoEvent,
  stepNeedsTourDemoEvent,
} from './ensureTourDemoEvent'
import {
  ensureGuidedTourDemoTimeEntries,
  stepNeedsTourDemoTimeEntry,
} from './ensureTourDemoTimeEntry'
import {
  ensureGuidedTourDemoDocument,
  stepNeedsTourDemoDocument,
} from './ensureTourDemoDocument'

export type TourNotify = (message: string) => void

export async function ensureChatRowForStep(
  step: GuidedTourStepDef,
  currentUserSub: string | undefined,
  setDemoChat: (chatId: string | null) => void,
  invalidateAfterSeed: (chatId: string) => Promise<void>,
  notify: TourNotify,
): Promise<{ status: 'ok'; chatId: string } | { status: 'failed' }> {
  if (!stepNeedsTourChatSeed(step)) return { status: 'ok', chatId: '' }
  if (!currentUserSub) {
    notify('Не удалось подготовить учебный чат: пользователь не определён.')
    return { status: 'failed' }
  }
  const cachedChatId = useTourStore.getState().demoChatId
  try {
    const result = await ensureGuidedTourDemoChat(currentUserSub, cachedChatId)
    if (!result.ok) {
      notify(result.reason)
      return { status: 'failed' }
    }
    setDemoChat(result.chatId)
    if (cachedChatId) {
      return { status: 'ok', chatId: result.chatId }
    }
    if (result.created || result.messageEnsured) {
      await invalidateAfterSeed(result.chatId)
    }
    const row = await waitForTourChatRow(5000)
    if (!row) {
      notify(
        'Учебный чат подготовлен, но список чатов ещё не обновился. Обновите страницу и продолжите обучение.',
      )
      return { status: 'failed' }
    }
    return { status: 'ok', chatId: result.chatId }
  } catch (e: unknown) {
    notify(userFacingMessageFromUnknown(e))
    return { status: 'failed' }
  }
}

export async function ensureDemoTaskForStep(
  step: GuidedTourStepDef,
  currentUserSub: string | undefined,
  setDemoTask: (taskId: string | null, prefill: TourDemoTaskPrefill | null) => void,
  invalidateTasks: () => Promise<void>,
  notify: TourNotify,
): Promise<{ status: 'ok' } | { status: 'failed' }> {
  if (!stepNeedsTourDemoTask(step)) return { status: 'ok' }
  if (!currentUserSub) {
    notify('Не удалось подготовить учебную задачу: пользователь не определён.')
    return { status: 'failed' }
  }
  try {
    const result = await ensureGuidedTourDemoTask(currentUserSub)
    if (!result.ok) {
      notify(result.reason)
      return { status: 'failed' }
    }
    setDemoTask(result.taskId, result.prefill)
    if (result.created) {
      await invalidateTasks()
    }
    return { status: 'ok' }
  } catch (e: unknown) {
    notify(userFacingMessageFromUnknown(e))
    return { status: 'failed' }
  }
}

export async function ensureDemoSpecialistForStep(
  step: GuidedTourStepDef,
  currentUserSub: string | undefined,
  setDemoSpecialist: (specialistSub: string | null, created: boolean) => void,
  invalidateBoard: () => Promise<void>,
  notify: TourNotify,
): Promise<{ status: 'ok' } | { status: 'failed' }> {
  if (!stepNeedsTourDemoSpecialist(step)) return { status: 'ok' }
  if (!currentUserSub) {
    notify('Не удалось подготовить учебного специалиста: пользователь не определён.')
    return { status: 'failed' }
  }
  try {
    const result = await ensureGuidedTourDemoSpecialist(currentUserSub)
    if (!result.ok) {
      notify(result.reason)
      return { status: 'failed' }
    }
    setDemoSpecialist(result.specialistSub, result.created)
    if (result.created) {
      await invalidateBoard()
      const card = await waitForTourTarget('[data-tour="specialists-kanban-card"]', 5000, 80)
      if (!card) {
        notify(
          'Учебный специалист добавлен, но доска ещё не обновилась. Обновите страницу и продолжите обучение.',
        )
        return { status: 'failed' }
      }
    }
    return { status: 'ok' }
  } catch (e: unknown) {
    notify(userFacingMessageFromUnknown(e))
    return { status: 'failed' }
  }
}

export async function ensureDemoEventForStep(
  step: GuidedTourStepDef,
  currentUserSub: string | undefined,
  setDemoEvent: (eventId: string | null) => void,
  invalidateCalendar: () => Promise<void>,
  notify: TourNotify,
): Promise<{ status: 'ok' } | { status: 'failed' }> {
  if (!stepNeedsTourDemoEvent(step)) return { status: 'ok' }
  if (!currentUserSub) {
    notify('Не удалось подготовить учебное событие: пользователь не определён.')
    return { status: 'failed' }
  }
  try {
    const result = await ensureGuidedTourDemoEvent(currentUserSub)
    if (!result.ok) {
      notify(result.reason)
      return { status: 'failed' }
    }
    setDemoEvent(result.eventId)
    if (result.created) {
      await invalidateCalendar()
    }
    return { status: 'ok' }
  } catch (e: unknown) {
    notify(userFacingMessageFromUnknown(e))
    return { status: 'failed' }
  }
}

export async function ensureDemoTimeEntriesForStep(
  step: GuidedTourStepDef,
  setDemoTimeEntries: (entryIds: string[]) => void,
  invalidateTimeEntries: () => Promise<void>,
  notify: TourNotify,
): Promise<{ status: 'ok' } | { status: 'failed' }> {
  if (!stepNeedsTourDemoTimeEntry(step)) return { status: 'ok' }
  try {
    const result = await ensureGuidedTourDemoTimeEntries()
    if (!result.ok) {
      notify(result.reason)
      return { status: 'failed' }
    }
    setDemoTimeEntries(result.entryIds)
    if (result.created) {
      await invalidateTimeEntries()
    }
    return { status: 'ok' }
  } catch (e: unknown) {
    notify(userFacingMessageFromUnknown(e))
    return { status: 'failed' }
  }
}

export async function ensureDemoDocumentForStep(
  step: GuidedTourStepDef,
  setDemoDocument: (documentId: string | null, created: boolean) => void,
  invalidateNavigation: () => Promise<void>,
  notify: TourNotify,
): Promise<{ status: 'ok'; documentId: string | null } | { status: 'failed' }> {
  if (!stepNeedsTourDemoDocument(step)) return { status: 'ok', documentId: null }
  try {
    const result = await ensureGuidedTourDemoDocument()
    if (!result.ok) {
      notify(result.reason)
      return { status: 'failed' }
    }
    setDemoDocument(result.documentId, result.created)
    await invalidateNavigation()
    if (step.id === 'nav-documents') {
      const navLink = `a[href="/documents/${encodeURIComponent(result.documentId)}"]`
      const link = await waitForTourTarget(navLink, 5000, 80)
      if (!link) {
        notify(
          'Учебный документ создан, но меню ещё не обновилось. Обновите страницу и продолжите обучение.',
        )
        return { status: 'failed' }
      }
    }
    return { status: 'ok', documentId: result.documentId }
  } catch (e: unknown) {
    notify(userFacingMessageFromUnknown(e))
    return { status: 'failed' }
  }
}
