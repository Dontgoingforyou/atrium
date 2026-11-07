/** Пресеты смещения напоминания (минуты до начала). */
export const CALENDAR_REMINDER_OFFSET_PRESETS = [0, 5, 15, 30, 60, 1440] as const

export const CALENDAR_MAX_REMINDERS = 5

export const DEFAULT_REMINDER_OFFSET_MINUTES = 15

export function reminderOffsetLabelRu(offsetMinutes: number): string {
  if (offsetMinutes === 0) return 'В момент начала'
  if (offsetMinutes < 60) return `За ${offsetMinutes} мин`
  if (offsetMinutes === 60) return 'За 1 час'
  if (offsetMinutes % 1440 === 0) {
    const days = offsetMinutes / 1440
    return days === 1 ? 'За 1 день' : `За ${days} дн.`
  }
  if (offsetMinutes % 60 === 0) {
    const hours = offsetMinutes / 60
    return `За ${hours} ч`
  }
  return `За ${offsetMinutes} мин`
}
