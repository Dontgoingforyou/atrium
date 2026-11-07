import { create } from 'zustand'

import {
  advanceGuidedTourStep,
  retreatGuidedTourStep,
  skipGuidedTourStep,
  type GuidedTourPhase,
  type GuidedTourStepDef,
} from '../domain/onboarding/guidedTour'
import { resetTourDemoChatSeed } from './ensureTourDemoChat'
import type { TourDemoTaskPrefill } from './ensureTourDemoTask'

export type GuidedTourUiMode = 'linear' | 'hint'

type TourStore = {
  phase: GuidedTourPhase
  mode: GuidedTourUiMode
  stepIndex: number
  steps: GuidedTourStepDef[]
  hasEnteredRunning: boolean
  hintFrozenLocationKeys: string[]
  demoTaskId: string | null
  demoTaskPrefill: TourDemoTaskPrefill | null
  /** specialist_sub учебной записи на доске; удалять только если demoSpecialistCreated. */
  demoSpecialistSub: string | null
  demoSpecialistCreated: boolean
  demoEventId: string | null
  demoChatId: string | null
  demoTimeEntryIds: string[]
  demoDocumentId: string | null
  demoDocumentCreated: boolean
  openWelcome: (steps: GuidedTourStepDef[]) => void
  startRunning: () => void
  startHint: (steps: GuidedTourStepDef[]) => void
  openDone: () => void
  resetIdle: () => void
  setHintFrozenLocationKeys: (keys: string[]) => void
  next: () => void
  back: () => void
  skipMissing: () => void
  setDemoTask: (taskId: string | null, prefill: TourDemoTaskPrefill | null) => void
  setDemoSpecialist: (specialistSub: string | null, created: boolean) => void
  setDemoEvent: (eventId: string | null) => void
  setDemoChat: (chatId: string | null) => void
  setDemoTimeEntries: (entryIds: string[]) => void
  setDemoDocument: (documentId: string | null, created: boolean) => void
  restartWithSteps: (steps: GuidedTourStepDef[]) => void
}

const initial = {
  phase: 'idle' as GuidedTourPhase,
  mode: 'linear' as GuidedTourUiMode,
  stepIndex: 0,
  steps: [] as GuidedTourStepDef[],
  hasEnteredRunning: false,
  hintFrozenLocationKeys: [] as string[],
  demoTaskId: null as string | null,
  demoTaskPrefill: null as TourDemoTaskPrefill | null,
  demoSpecialistSub: null as string | null,
  demoSpecialistCreated: false,
  demoEventId: null as string | null,
  demoChatId: null as string | null,
  demoTimeEntryIds: [] as string[],
  demoDocumentId: null as string | null,
  demoDocumentCreated: false,
}

export const useTourStore = create<TourStore>((set, get) => ({
  ...initial,
  openWelcome: (steps) => {
    resetTourDemoChatSeed()
    set({
      ...initial,
      phase: 'welcome',
      mode: 'linear',
      steps,
    })
  },
  startRunning: () => {
    const { steps } = get()
    if (steps.length === 0) {
      set({ phase: 'done', hasEnteredRunning: true })
      return
    }
    set({ phase: 'running', stepIndex: 0, hasEnteredRunning: true })
  },
  startHint: (steps) => {
    if (steps.length === 0) return
    resetTourDemoChatSeed()
    set({
      ...initial,
      hintFrozenLocationKeys: get().hintFrozenLocationKeys,
      phase: 'running',
      mode: 'hint',
      steps,
      hasEnteredRunning: true,
    })
  },
  openDone: () => set({ phase: 'done' }),
  resetIdle: () => {
    resetTourDemoChatSeed()
    set({ ...initial, hintFrozenLocationKeys: get().hintFrozenLocationKeys })
  },
  setHintFrozenLocationKeys: (keys) => set({ hintFrozenLocationKeys: keys }),
  next: () => {
    const cur = get()
    const nextState = advanceGuidedTourStep({
      phase: cur.phase,
      stepIndex: cur.stepIndex,
      steps: cur.steps,
    })
    set({
      phase: nextState.phase,
      stepIndex: nextState.stepIndex,
    })
  },
  back: () => {
    const cur = get()
    const nextState = retreatGuidedTourStep({
      phase: cur.phase,
      stepIndex: cur.stepIndex,
      steps: cur.steps,
    })
    set({
      stepIndex: nextState.stepIndex,
    })
  },
  skipMissing: () => {
    const cur = get()
    const nextState = skipGuidedTourStep({
      phase: cur.phase,
      stepIndex: cur.stepIndex,
      steps: cur.steps,
    })
    set({
      phase: nextState.phase,
      stepIndex: nextState.stepIndex,
    })
  },
  setDemoTask: (taskId, prefill) => set({ demoTaskId: taskId, demoTaskPrefill: prefill }),
  setDemoSpecialist: (specialistSub, created) =>
    set({
      demoSpecialistSub: specialistSub,
      demoSpecialistCreated: specialistSub ? created : false,
    }),
  setDemoEvent: (eventId) => set({ demoEventId: eventId }),
  setDemoChat: (chatId) => set({ demoChatId: chatId }),
  setDemoTimeEntries: (entryIds) => set({ demoTimeEntryIds: entryIds }),
  setDemoDocument: (documentId, created) =>
    set({
      demoDocumentId: documentId,
      demoDocumentCreated: documentId ? created : false,
    }),
  restartWithSteps: (steps) => {
    resetTourDemoChatSeed()
    set({
      ...initial,
      phase: 'welcome',
      mode: 'linear',
      steps,
    })
  },
}))
