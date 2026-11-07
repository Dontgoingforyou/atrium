import { describe, expect, it } from 'vitest'

import {
  releaseMessageSubmitLock,
  tryAcquireMessageSubmitLock,
} from '@/utils/chat/messageInputSubmit'

describe('messageInputSubmit lock', () => {
  it('второй acquire подряд отклоняется до release', () => {
    const inFlight = { current: false }
    expect(tryAcquireMessageSubmitLock(inFlight)).toBe(true)
    expect(tryAcquireMessageSubmitLock(inFlight)).toBe(false)
    releaseMessageSubmitLock(inFlight)
    expect(tryAcquireMessageSubmitLock(inFlight)).toBe(true)
    releaseMessageSubmitLock(inFlight)
  })
})
