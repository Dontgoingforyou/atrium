import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { persistHintPageSeen, persistLinearTourSeen } from '../../src/onboarding/persistTourSeen'
import { readGuidedTourSeenStepIds } from '../../src/onboarding/guidedTourSeenStorage'
import type { GuidedTourStepDef } from '../../src/domain/onboarding/guidedTour'

let store: Record<string, string> = {}

function installLocalStorageStub() {
  const stub = {
    getItem: (k: string): string | null => (Object.hasOwn(store, k) ? store[k] : null),
    setItem: (k: string, v: string): void => {
      store[k] = String(v)
    },
    removeItem: (k: string): void => {
      delete store[k]
    },
    clear: (): void => {
      store = {}
    },
  }
  ;(globalThis as unknown as { localStorage: typeof stub }).localStorage = stub
}

beforeEach(() => {
  store = {}
  installLocalStorageStub()
})

afterEach(() => {
  store = {}
  delete (globalThis as unknown as { localStorage?: unknown }).localStorage
})

const steps: GuidedTourStepDef[] = [
  { id: 'a', title: 'A', body: 'a' },
  { id: 'b', title: 'B', body: 'b' },
  { id: 'c', title: 'C', body: 'c' },
]

describe('persistTourSeen', () => {
  it('welcome skip writes empty seen', () => {
    persistLinearTourSeen({
      userSub: 'u',
      steps,
      stepIndex: 0,
      hasEnteredRunning: false,
    })
    expect([...readGuidedTourSeenStepIds('u')]).toEqual([])
  })

  it('skip at middle keeps 0..N', () => {
    persistLinearTourSeen({
      userSub: 'u',
      steps,
      stepIndex: 1,
      hasEnteredRunning: true,
    })
    expect([...readGuidedTourSeenStepIds('u')]).toEqual(['a', 'b'])
  })

  it('linear complete on last step marks all', () => {
    persistLinearTourSeen({
      userSub: 'u',
      steps,
      stepIndex: 2,
      hasEnteredRunning: true,
    })
    expect([...readGuidedTourSeenStepIds('u')]).toEqual(['a', 'b', 'c'])
  })

  it('hint page adds remaining ids', () => {
    persistLinearTourSeen({
      userSub: 'u',
      steps,
      stepIndex: 0,
      hasEnteredRunning: true,
    })
    persistHintPageSeen('u', [steps[2]])
    expect([...readGuidedTourSeenStepIds('u')]).toEqual(['a', 'c'])
  })
})
