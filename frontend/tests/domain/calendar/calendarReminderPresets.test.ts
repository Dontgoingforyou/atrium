import { describe, expect, it } from 'vitest'

import {
  CALENDAR_MAX_REMINDERS,
  CALENDAR_REMINDER_OFFSET_PRESETS,
  DEFAULT_REMINDER_OFFSET_MINUTES,
  reminderOffsetLabelRu,
} from '../../../src/domain/calendar/calendarReminderPresets'

describe('calendarReminderPresets', () => {
  it('экспортирует пресеты и лимиты', () => {
    expect(CALENDAR_REMINDER_OFFSET_PRESETS).toEqual([0, 5, 15, 30, 60, 1440])
    expect(CALENDAR_MAX_REMINDERS).toBe(5)
    expect(DEFAULT_REMINDER_OFFSET_MINUTES).toBe(15)
  })

  it('reminderOffsetLabelRu для типовых смещений', () => {
    expect(reminderOffsetLabelRu(0)).toBe('В момент начала')
    expect(reminderOffsetLabelRu(5)).toBe('За 5 мин')
    expect(reminderOffsetLabelRu(60)).toBe('За 1 час')
    expect(reminderOffsetLabelRu(120)).toBe('За 2 ч')
    expect(reminderOffsetLabelRu(1440)).toBe('За 1 день')
    expect(reminderOffsetLabelRu(2880)).toBe('За 2 дн.')
    expect(reminderOffsetLabelRu(90)).toBe('За 90 мин')
  })
})
