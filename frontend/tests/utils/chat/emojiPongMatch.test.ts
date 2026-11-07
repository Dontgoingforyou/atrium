import { describe, expect, it } from 'vitest'

import { shouldAcceptPeerInviteWhileWaiting } from '@/utils/chat/emojiPongMatch'

describe('shouldAcceptPeerInviteWhileWaiting', () => {
  it('принимает чужой инвайт с меньшим session_id', () => {
    expect(shouldAcceptPeerInviteWhileWaiting('bbb-2', 'aaa-1')).toBe(true)
  })

  it('остаётся хостом при своём меньшем session_id', () => {
    expect(shouldAcceptPeerInviteWhileWaiting('aaa-1', 'bbb-2')).toBe(false)
  })
})
