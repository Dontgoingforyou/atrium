// @vitest-environment jsdom

import { beforeEach, describe, expect, it } from 'vitest'

import { toWsUrl } from '@/hooks/ws/url'

beforeEach(() => {
  Object.defineProperty(window, 'location', {
    configurable: true,
    value: { origin: 'https://portal.test' },
  })
})

describe('toWsUrl', () => {
  it('относительный apiBase — через window.location.origin', () => {
    expect(toWsUrl('/api/v1', '/portal/inbox/ws?ticket=abc')).toBe(
      'wss://portal.test/api/v1/portal/inbox/ws?ticket=abc',
    )
  })

  it('абсолютный https apiBase → wss://', () => {
    expect(toWsUrl('https://api.example.com/api/v1', '/portal/chats/1/ws')).toBe(
      'wss://api.example.com/api/v1/portal/chats/1/ws',
    )
  })

  it('абсолютный http apiBase → ws://', () => {
    expect(toWsUrl('http://localhost:8000/api/v1', '/portal/tasks/board/ws')).toBe(
      'ws://localhost:8000/api/v1/portal/tasks/board/ws',
    )
  })

  it('не двойной слэш при path с ведущим /', () => {
    expect(toWsUrl('https://api.example.com/api/v1', '/x')).toBe(
      'wss://api.example.com/api/v1/x',
    )
  })

  it('https → wss, http → ws (префикс http в https)', () => {
    expect(toWsUrl('https://a.test/v1', '/ws')).toMatch(/^wss:\/\//)
    expect(toWsUrl('http://a.test/v1', '/ws')).toMatch(/^ws:\/\//)
    expect(toWsUrl('http://a.test/v1', '/ws')).not.toMatch(/^wss:\/\//)
  })

  it('path без ведущего / склеивается как есть (контракт call site — ведущий /)', () => {
    expect(toWsUrl('https://api.example.com/api/v1', 'x')).toBe(
      'wss://api.example.com/api/v1x',
    )
  })
})
