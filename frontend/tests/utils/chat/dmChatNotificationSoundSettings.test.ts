// @vitest-environment jsdom

import { afterEach, describe, expect, it } from 'vitest'

import { DM_NOTIFICATION_SOUND_BY_CHAT_KEY } from '../../../src/constants/chatStorage'
import {
  getDmChatNotificationSoundEnabled,
  setDmChatNotificationSoundEnabled,
} from '../../../src/utils/chat/dmChatNotificationSoundSettings'

afterEach(() => {
  localStorage.clear()
})

describe('dmChatNotificationSoundSettings', () => {
  it('по умолчанию включено', () => {
    expect(getDmChatNotificationSoundEnabled('chat-1')).toBe(true)
  })

  it('выключение пишет false, включение удаляет ключ', () => {
    setDmChatNotificationSoundEnabled('chat-1', false)
    expect(getDmChatNotificationSoundEnabled('chat-1')).toBe(false)
    setDmChatNotificationSoundEnabled('chat-1', true)
    expect(getDmChatNotificationSoundEnabled('chat-1')).toBe(true)
    expect(localStorage.getItem(DM_NOTIFICATION_SOUND_BY_CHAT_KEY)).toBeNull()
  })

  it('битый JSON в storage → звук по умолчанию включён', () => {
    localStorage.setItem(DM_NOTIFICATION_SOUND_BY_CHAT_KEY, '{not-json')
    expect(getDmChatNotificationSoundEnabled('chat-1')).toBe(true)
    localStorage.setItem(DM_NOTIFICATION_SOUND_BY_CHAT_KEY, '[]')
    expect(getDmChatNotificationSoundEnabled('chat-1')).toBe(true)
  })
})
