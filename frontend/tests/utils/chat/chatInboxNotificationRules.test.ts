import { describe, expect, it } from 'vitest'

import {
  shouldShowChatInboxToast,
  shouldSuppressChatInboxToast,
  shouldSuppressDueToMute,
} from '@/utils/chat/chatInboxNotificationRules'

describe('shouldSuppressChatInboxToast', () => {
  it('не подавляет, если вкладка не видима', () => {
    expect(
      shouldSuppressChatInboxToast({
        eventChatId: 'c1',
        pathname: '/chats',
        search: '?chat=c1',
        visibilityState: 'hidden',
        focused: { chatsPage: null, widget: null },
      }),
    ).toBe(false)
  })

  it('подавляет при совпадении ?chat= на /chats и видимой вкладке', () => {
    expect(
      shouldSuppressChatInboxToast({
        eventChatId: 'abc',
        pathname: '/chats',
        search: '?chat=abc',
        visibilityState: 'visible',
        focused: { chatsPage: null, widget: null },
      }),
    ).toBe(true)
  })

  it('подавляет при совпадении с чатом из плавающего виджета', () => {
    expect(
      shouldSuppressChatInboxToast({
        eventChatId: 'w1',
        pathname: '/tasks',
        search: '',
        visibilityState: 'visible',
        focused: { chatsPage: null, widget: 'w1' },
      }),
    ).toBe(true)
  })

  it('не путает другой chat в URL и префикс /chatsfoo', () => {
    expect(
      shouldSuppressChatInboxToast({
        eventChatId: 'c1',
        pathname: '/chats',
        search: '?chat=c2',
        visibilityState: 'visible',
        focused: { chatsPage: null, widget: null },
      }),
    ).toBe(false)
    expect(
      shouldSuppressChatInboxToast({
        eventChatId: 'c1',
        pathname: '/chats',
        search: '?chat=c1evil',
        visibilityState: 'visible',
        focused: { chatsPage: null, widget: null },
      }),
    ).toBe(false)
    expect(
      shouldSuppressChatInboxToast({
        eventChatId: 'c1',
        pathname: '/chatsfoo',
        search: '?chat=c1',
        visibilityState: 'visible',
        focused: { chatsPage: null, widget: null },
      }),
    ).toBe(false)
  })
})

describe('shouldShowChatInboxToast', () => {
  const base = {
    eventChatId: 'c1',
    pathname: '/tasks',
    search: '',
    visibilityState: 'visible' as const,
    focused: { chatsPage: null, widget: null },
    toastEnabled: true,
    chatMuted: false,
    isMentioned: false,
  }

  it('не показывает, если пользователь уже в этом чате', () => {
    expect(
      shouldShowChatInboxToast({
        ...base,
        pathname: '/chats',
        search: '?chat=c1',
      }),
    ).toBe(false)
  })

  it('не показывает замьюченный чат без упоминания', () => {
    expect(shouldShowChatInboxToast({ ...base, chatMuted: true })).toBe(false)
    expect(shouldSuppressDueToMute(true, false)).toBe(true)
  })

  it('показывает замьюченный чат при @упоминании', () => {
    expect(shouldShowChatInboxToast({ ...base, chatMuted: true, isMentioned: true })).toBe(true)
  })

  it('не показывает, если тост выключен в настройках', () => {
    expect(shouldShowChatInboxToast({ ...base, toastEnabled: false })).toBe(false)
  })
})
