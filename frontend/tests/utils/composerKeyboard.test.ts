import { describe, expect, it, vi } from 'vitest'
import type { KeyboardEvent } from 'react'

import { handleComposerEnterSubmit } from '../../src/utils/composerKeyboard'

function keyEvent(partial: Partial<KeyboardEvent<HTMLTextAreaElement>>): KeyboardEvent<HTMLTextAreaElement> {
  return {
    key: 'Enter',
    shiftKey: false,
    preventDefault: vi.fn(),
    stopPropagation: vi.fn(),
    ...partial,
  } as KeyboardEvent<HTMLTextAreaElement>
}

describe('handleComposerEnterSubmit', () => {
  it('не Enter / Shift+Enter → false', () => {
    const submit = vi.fn()
    expect(handleComposerEnterSubmit(keyEvent({ key: 'a' }), true, submit)).toBe(false)
    expect(handleComposerEnterSubmit(keyEvent({ shiftKey: true }), true, submit)).toBe(false)
    expect(submit).not.toHaveBeenCalled()
  })

  it('Enter: preventDefault и submit при canSubmit', () => {
    const submit = vi.fn()
    const e = keyEvent({})
    expect(handleComposerEnterSubmit(e, true, submit)).toBe(true)
    expect(e.preventDefault).toHaveBeenCalled()
    expect(e.stopPropagation).toHaveBeenCalled()
    expect(submit).toHaveBeenCalledOnce()
  })

  it('Enter без canSubmit — не вызывает submit', () => {
    const submit = vi.fn()
    expect(handleComposerEnterSubmit(keyEvent({}), false, submit)).toBe(true)
    expect(submit).not.toHaveBeenCalled()
  })
})
