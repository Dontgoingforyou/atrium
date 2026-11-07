// @vitest-environment jsdom

import { afterEach, describe, expect, it } from 'vitest'

import {
  DEFAULT_CHAT_DM_SOUND_ID,
  DEFAULT_NOTIFICATION_SOUND_ID,
} from '@/domain/sound/soundPresets'
import {
  getChatDmSoundUrl,
  getChatDmSoundVolumePct,
  getNotificationSoundUrl,
  getNotificationSoundVolumePct,
  getResolvedChatDmSoundId,
  getResolvedNotificationSoundId,
  normalizeSoundVolumePct,
  setChatDmSoundPresetId,
  setChatDmSoundVolumePct,
  setNotificationSoundPresetId,
  setNotificationSoundVolumePct,
} from '@/utils/notifications/soundChoiceStorage'

afterEach(() => {
  localStorage.clear()
})

describe('normalizeSoundVolumePct', () => {
  it('null → 100', () => {
    expect(normalizeSoundVolumePct(null)).toBe(100)
  })

  it('валидная строка → округление и clamp', () => {
    expect(normalizeSoundVolumePct('50')).toBe(50)
    expect(normalizeSoundVolumePct('150')).toBe(100)
    expect(normalizeSoundVolumePct('-5')).toBe(0)
    expect(normalizeSoundVolumePct('33.7')).toBe(34)
  })

  it('невалидное → 100', () => {
    expect(normalizeSoundVolumePct('')).toBe(100)
    expect(normalizeSoundVolumePct('abc')).toBe(100)
  })
})

describe('soundChoiceStorage presets', () => {
  it('дефолты без storage', () => {
    expect(getResolvedNotificationSoundId()).toBe(DEFAULT_NOTIFICATION_SOUND_ID)
    expect(getResolvedChatDmSoundId()).toBe(DEFAULT_CHAT_DM_SOUND_ID)
    expect(getNotificationSoundUrl()).toBe('/sounds/notification.wav')
    expect(getChatDmSoundUrl()).toBe('/sounds/new-message-for-you-man.wav')
  })

  it('сохраняет валидный preset и игнорирует неизвестный', () => {
    setNotificationSoundPresetId('cybernetic')
    expect(getResolvedNotificationSoundId()).toBe('cybernetic')
    expect(getNotificationSoundUrl()).toBe('/sounds/cybernetic.wav')

    setNotificationSoundPresetId('no-such-preset')
    expect(getResolvedNotificationSoundId()).toBe('cybernetic')

    setChatDmSoundPresetId('message-tone')
    expect(getResolvedChatDmSoundId()).toBe('message-tone')
  })

  it('неизвестный id уже в storage → дефолт и валидный URL', () => {
    localStorage.setItem('cosmolet:notification_sound_choice', 'deleted-preset')
    expect(getResolvedNotificationSoundId()).toBe(DEFAULT_NOTIFICATION_SOUND_ID)
    expect(getNotificationSoundUrl()).toBe('/sounds/notification.wav')
    localStorage.setItem('cosmolet:chat_dm_sound_choice', 'gone')
    expect(getResolvedChatDmSoundId()).toBe(DEFAULT_CHAT_DM_SOUND_ID)
  })
})

describe('soundChoiceStorage volume', () => {
  it('читает/пишет громкость с clamp', () => {
    expect(getNotificationSoundVolumePct()).toBe(100)
    setNotificationSoundVolumePct(40)
    expect(getNotificationSoundVolumePct()).toBe(40)
    setNotificationSoundVolumePct(200)
    expect(getNotificationSoundVolumePct()).toBe(100)

    setChatDmSoundVolumePct(-1)
    expect(getChatDmSoundVolumePct()).toBe(0)
  })
})
