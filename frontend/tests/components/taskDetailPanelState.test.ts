import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import {
  computeInitialOpen,
  isContentDrivenPanel,
  persistOpen,
  readInitialOpen,
  readStoredOpen,
  resolveAutoOpenState,
} from '../../src/components/tasks/detail/taskDetailPanelState'

// Среда Vitest — node (без jsdom): localStorage недоступен из коробки.
// taskDetailPanelState использует localStorage только на границе персистентности,
// поэтому покрываем минимальным in-memory стабом.
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

describe('isContentDrivenPanel', () => {
  it('content-driven панели возвращают true', () => {
    expect(isContentDrivenPanel('links')).toBe(true)
    expect(isContentDrivenPanel('files')).toBe(true)
    expect(isContentDrivenPanel('modal-comments')).toBe(true)
    expect(isContentDrivenPanel('spec-links')).toBe(true)
  })

  it('history, spec-profile и document-comments не content-driven', () => {
    expect(isContentDrivenPanel('history')).toBe(false)
    expect(isContentDrivenPanel('spec-profile')).toBe(false)
    expect(isContentDrivenPanel('document-comments')).toBe(false)
  })

  it('subtasks/comments — content-driven', () => {
    expect(isContentDrivenPanel('subtasks')).toBe(true)
    expect(isContentDrivenPanel('comments')).toBe(true)
  })
})

describe('readStoredOpen / persistOpen', () => {
  it('content-driven и history не сохраняются и читаются как undefined', () => {
    persistOpen('links', true)
    persistOpen('history', true)
    expect(readStoredOpen('links')).toBeUndefined()
    expect(readStoredOpen('history')).toBeUndefined()
    expect(localStorage.getItem('atrium.taskDetail.panelOpen.v1')).toBeNull()
  })

  it('spec-profile и произвольные панели сохраняются и читаются', () => {
    persistOpen('spec-profile', false)
    expect(readStoredOpen('spec-profile')).toBe(false)
    persistOpen('spec-profile', true)
    expect(readStoredOpen('spec-profile')).toBe(true)
  })

  it('отсутствие записи → undefined', () => {
    expect(readStoredOpen('spec-profile')).toBeUndefined()
  })

  it('битый JSON не бросает, возвращает undefined', () => {
    localStorage.setItem('atrium.taskDetail.panelOpen.v1', '{not json')
    expect(readStoredOpen('spec-profile')).toBeUndefined()
  })

  it('readInitialOpen учитывает сохранённое значение', () => {
    persistOpen('spec-profile', false)
    expect(readInitialOpen('spec-profile')).toBe(false)
  })

  it('readInitialOpen для spec-profile без записи → true (ALWAYS_OPEN)', () => {
    expect(readInitialOpen('spec-profile')).toBe(true)
  })

  it('readInitialOpen для document-comments без записи → true (ALWAYS_OPEN)', () => {
    expect(readInitialOpen('document-comments')).toBe(true)
  })

  it('readInitialOpen: history/comments по умолчанию свёрнуты', () => {
    expect(readInitialOpen('history')).toBe(false)
    expect(readInitialOpen('modal-history')).toBe(false)
    expect(readInitialOpen('comments')).toBe(false)
  })
})

describe('computeInitialOpen', () => {
  it('history всегда свёрнута', () => {
    expect(computeInitialOpen('history')).toBe(false)
    expect(computeInitialOpen('modal-history')).toBe(false)
    expect(computeInitialOpen('history', 10)).toBe(false)
  })

  it('content-driven: открытость по contentCount', () => {
    expect(computeInitialOpen('links', 5)).toBe(true)
    expect(computeInitialOpen('files', 0)).toBe(false)
  })

  it('content-driven без contentCount — свёрнута', () => {
    expect(computeInitialOpen('comments')).toBe(false)
  })

  it('spec-profile без записи — открыта', () => {
    expect(computeInitialOpen('spec-profile')).toBe(true)
  })

  it('document-comments без записи — открыта', () => {
    expect(computeInitialOpen('document-comments')).toBe(true)
  })

  it('сохранённый выбор пользователя перекрывает дефолт spec-profile', () => {
    persistOpen('spec-profile', false)
    expect(computeInitialOpen('spec-profile')).toBe(false)
  })
})

describe('resolveAutoOpenState', () => {
  it('history всегда false', () => {
    expect(resolveAutoOpenState('history', 5)).toBe(false)
    expect(resolveAutoOpenState('modal-history', 5)).toBe(false)
  })

  it('content-driven всегда явное значение по contentCount', () => {
    expect(resolveAutoOpenState('links', 3)).toBe(true)
    expect(resolveAutoOpenState('links', 0)).toBe(false)
    expect(resolveAutoOpenState('files', 2)).toBe(true)
    expect(resolveAutoOpenState('files', 0)).toBe(false)
    expect(resolveAutoOpenState('modal-files', 2)).toBe(true)
    expect(resolveAutoOpenState('modal-subtasks', 0)).toBe(false)
    expect(resolveAutoOpenState('extLinks', 1)).toBe(true)
  })

  it('content-driven не зависит от сохранённого выбора', () => {
    persistOpen('links', false)
    expect(resolveAutoOpenState('links', 3)).toBe(true)
    persistOpen('extLinks', false)
    expect(resolveAutoOpenState('extLinks', 5)).toBe(true)
  })

  it('spec-profile без записи → true', () => {
    expect(resolveAutoOpenState('spec-profile', 0)).toBe(true)
  })

  it('document-comments без записи → true', () => {
    expect(resolveAutoOpenState('document-comments', 0)).toBe(true)
  })

  it('есть сохранённый выбор → undefined (авто не перекрывает)', () => {
    persistOpen('spec-profile', false)
    expect(resolveAutoOpenState('spec-profile', 5)).toBeUndefined()
  })
})
