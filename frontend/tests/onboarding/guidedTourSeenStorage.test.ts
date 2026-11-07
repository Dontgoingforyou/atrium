import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { GUIDED_TOUR_SEEN_STEPS_KEY_PREFIX } from '../../src/constants/guidedTour'
import {
  addGuidedTourSeenStepIds,
  clearGuidedTourSeenStepIds,
  readGuidedTourSeenStepIds,
  writeGuidedTourSeenStepIds,
} from '../../src/onboarding/guidedTourSeenStorage'

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

describe('guidedTourSeenStorage', () => {
  it('writes and reads ids per user sub', () => {
    writeGuidedTourSeenStepIds('user-a', ['search', 'chats-sidebar'])
    expect([...readGuidedTourSeenStepIds('user-a')]).toEqual(['search', 'chats-sidebar'])
    expect([...readGuidedTourSeenStepIds('user-b')]).toEqual([])
    expect(store[`${GUIDED_TOUR_SEEN_STEPS_KEY_PREFIX}:user-a`]).toContain('search')
  })

  it('add merges without duplicates; clear empties', () => {
    addGuidedTourSeenStepIds('u', ['a'])
    addGuidedTourSeenStepIds('u', ['a', 'b'])
    expect([...readGuidedTourSeenStepIds('u')]).toEqual(['a', 'b'])
    clearGuidedTourSeenStepIds('u')
    expect([...readGuidedTourSeenStepIds('u')]).toEqual([])
  })

  it('мусор в storage не ломает чтение', () => {
    store[`${GUIDED_TOUR_SEEN_STEPS_KEY_PREFIX}:u`] = '{not-json'
    expect([...readGuidedTourSeenStepIds('u')]).toEqual([])
    store[`${GUIDED_TOUR_SEEN_STEPS_KEY_PREFIX}:u`] = '{"x":1}'
    expect([...readGuidedTourSeenStepIds('u')]).toEqual([])
  })

  it('пустой sub не пишет в storage', () => {
    writeGuidedTourSeenStepIds('', ['a'])
    addGuidedTourSeenStepIds('  ', ['b'])
    expect(Object.keys(store)).toEqual([])
  })
})
