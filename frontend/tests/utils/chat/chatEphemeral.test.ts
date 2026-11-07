import { describe, expect, it } from 'vitest'

import { formatEphemeralHint } from '@/utils/chat/chatEphemeral'

describe('formatEphemeralHint', () => {
  it('возвращает null для пустого списка', () => {
    expect(formatEphemeralHint([])).toBeNull()
  })

  it('форматирует одного печатающего', () => {
    expect(
      formatEphemeralHint([{ userSub: 'a', displayName: 'Alice', kind: 'typing' }]),
    ).toBe('Alice печатает…')
  })

  it('форматирует голосовую запись', () => {
    expect(
      formatEphemeralHint([{ userSub: 'b', displayName: 'Bob', kind: 'voice_recording' }]),
    ).toBe('Bob записывает голосовое…')
  })

  it('агрегирует typing и voice', () => {
    const hint = formatEphemeralHint([
      { userSub: 'a', displayName: 'Alice', kind: 'typing' },
      { userSub: 'b', displayName: 'Bob', kind: 'voice_recording' },
    ])
    expect(hint).toContain('Alice печатает')
    expect(hint).toContain('Bob записывает голосовое')
  })
})
