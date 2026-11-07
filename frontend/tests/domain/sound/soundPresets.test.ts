import { describe, expect, it } from 'vitest'

import {
  DEFAULT_CHAT_DM_SOUND_ID,
  DEFAULT_NOTIFICATION_SOUND_ID,
  findPresetById,
  resolveStoredPresetId,
  urlForPresetId,
} from '../../../src/domain/sound/soundPresets'

describe('soundPresets', () => {
  it('resolveStoredPresetId: валидный id сохраняется', () => {
    expect(resolveStoredPresetId('cybernetic', DEFAULT_NOTIFICATION_SOUND_ID)).toBe('cybernetic')
  })

  it('resolveStoredPresetId: null → дефолт уведомлений', () => {
    expect(resolveStoredPresetId(null, DEFAULT_NOTIFICATION_SOUND_ID)).toBe(DEFAULT_NOTIFICATION_SOUND_ID)
  })

  it('resolveStoredPresetId: неизвестный id → дефолт', () => {
    expect(resolveStoredPresetId('no-such-preset', DEFAULT_NOTIFICATION_SOUND_ID)).toBe(
      DEFAULT_NOTIFICATION_SOUND_ID,
    )
    expect(resolveStoredPresetId('garbage', DEFAULT_CHAT_DM_SOUND_ID)).toBe(DEFAULT_CHAT_DM_SOUND_ID)
  })

  it('findPresetById и urlForPresetId для дефолтов', () => {
    expect(findPresetById(DEFAULT_NOTIFICATION_SOUND_ID)?.url).toBe('/sounds/notification.wav')
    expect(urlForPresetId(DEFAULT_CHAT_DM_SOUND_ID)).toBe('/sounds/new-message-for-you-man.wav')
  })

  it('findPresetById для произвольного пресета из списка', () => {
    expect(findPresetById('bright-clear-ring')?.label).toContain('Ясный')
  })

  it('findPresetById для mp3-пресета sms-posmotri-vdrug', () => {
    expect(findPresetById('sms-posmotri-vdrug')?.url).toBe('/sounds/sms-posmotri-vdrug.mp3')
  })
})
