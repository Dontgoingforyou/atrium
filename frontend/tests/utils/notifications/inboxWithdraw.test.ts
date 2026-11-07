import { describe, expect, it } from 'vitest'

import {
  DM_INBOX_WITHDRAWN_EVENT,
  PORTAL_NOTIFICATION_UPDATE_EVENT,
  PORTAL_NOTIFICATION_WITHDRAWN_EVENT,
  chatInboxOsNotificationTag,
  closeTrackedChatInboxOsNotification,
  portalNotificationEventPlaysSound,
  shouldDismissChatInboxToast,
  trackChatInboxOsNotification,
} from '@/utils/notifications/inboxWithdraw'

describe('portalNotificationEventPlaysSound', () => {
  it('играет звук только на новое уведомление', () => {
    expect(portalNotificationEventPlaysSound(PORTAL_NOTIFICATION_UPDATE_EVENT)).toBe(true)
  })

  it('не играет звук на отзыв после удаления', () => {
    expect(portalNotificationEventPlaysSound(PORTAL_NOTIFICATION_WITHDRAWN_EVENT)).toBe(false)
    expect(portalNotificationEventPlaysSound(DM_INBOX_WITHDRAWN_EVENT)).toBe(false)
  })
})

describe('shouldDismissChatInboxToast', () => {
  it('закрывает тост того же чата', () => {
    expect(shouldDismissChatInboxToast('chat-1', 'chat-1')).toBe(true)
  })

  it('не закрывает тост другого чата и пустой тост', () => {
    expect(shouldDismissChatInboxToast('chat-1', 'chat-2')).toBe(false)
    expect(shouldDismissChatInboxToast(null, 'chat-1')).toBe(false)
    expect(shouldDismissChatInboxToast(undefined, 'chat-1')).toBe(false)
  })
})

describe('closeTrackedChatInboxOsNotification', () => {
  it('закрывает системное уведомление по тегу чата', () => {
    let closed = 0
    trackChatInboxOsNotification('chat-9', { close: () => { closed += 1 } })
    expect(chatInboxOsNotificationTag('chat-9')).toBe('portal-chat-chat-9')
    closeTrackedChatInboxOsNotification('chat-9')
    expect(closed).toBe(1)
    closeTrackedChatInboxOsNotification('chat-9')
    expect(closed).toBe(1)
  })
})
