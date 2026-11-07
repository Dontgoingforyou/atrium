// @vitest-environment jsdom

import { afterEach, describe, expect, it } from 'vitest'

import {
  CHAT_INBOX_BROWSER_OS_ENABLED_KEY,
  CHAT_INBOX_TOAST_ENABLED_KEY,
} from '../../../src/constants/chatStorage'
import {
  getChatInboxBrowserOsEnabled,
  getChatInboxToastEnabled,
  getChatWebPushSubscriptionOptIn,
  setChatInboxBrowserOsEnabled,
  setChatInboxToastEnabled,
  setChatWebPushSubscriptionOptIn,
} from '../../../src/utils/chat/chatBrowserNotificationSettings'

afterEach(() => {
  localStorage.clear()
})

describe('chatBrowserNotificationSettings', () => {
  it('toast по умолчанию включён, OS/push — выключены', () => {
    expect(getChatInboxToastEnabled()).toBe(true)
    expect(getChatInboxBrowserOsEnabled()).toBe(false)
    expect(getChatWebPushSubscriptionOptIn()).toBe(false)
  })

  it('setters переключают флаги', () => {
    setChatInboxToastEnabled(false)
    expect(getChatInboxToastEnabled()).toBe(false)
    setChatInboxBrowserOsEnabled(true)
    expect(getChatInboxBrowserOsEnabled()).toBe(true)
    setChatWebPushSubscriptionOptIn(true)
    expect(getChatWebPushSubscriptionOptIn()).toBe(true)
  })

  it('мусор в localStorage не включает флаги (только "1")', () => {
    localStorage.setItem(CHAT_INBOX_TOAST_ENABLED_KEY, 'true')
    expect(getChatInboxToastEnabled()).toBe(false)
    localStorage.setItem(CHAT_INBOX_BROWSER_OS_ENABLED_KEY, 'yes')
    expect(getChatInboxBrowserOsEnabled()).toBe(false)
  })
})
