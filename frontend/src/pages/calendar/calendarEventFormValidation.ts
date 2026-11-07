import { joinLocal } from '../../domain/calendar/calendarLocalTime'

export type CalendarEventFieldKey = 'title' | 'calendar' | 'starts' | 'ends' | 'attendees'

export type CalendarEventFieldErrors = Partial<Record<CalendarEventFieldKey, string>>

export type CalendarEventFormValues = {
  title: string
  calendarId: string
  startDate: string
  startTime: string
  endDate: string
  endTime: string
  noEnd: boolean
  guestSubs: string[]
}

export const MSG_TITLE_REQUIRED = 'Укажите название'
export const MSG_CALENDAR_REQUIRED = 'Выберите календарь'
export const MSG_STARTS_REQUIRED = 'Укажите дату и время начала'
export const MSG_ENDS_REQUIRED = 'Укажите окончание или отметьте «Без окончания»'
export const MSG_END_AFTER_START = 'Окончание события должно быть позже начала'
export const MSG_ATTENDEES_REQUIRED = 'Укажите хотя бы одного участника'

/** Клиентская валидация формы события; пустой объект — форма валидна. */
export function validateCalendarEventForm(
  values: CalendarEventFormValues,
): CalendarEventFieldErrors {
  const errors: CalendarEventFieldErrors = {}

  if (!values.title.trim()) {
    errors.title = MSG_TITLE_REQUIRED
  }
  if (!values.calendarId) {
    errors.calendar = MSG_CALENDAR_REQUIRED
  }

  if (!values.startDate.trim()) {
    errors.starts = MSG_STARTS_REQUIRED
  }

  const startsLocal = values.startDate.trim()
    ? joinLocal(values.startDate, values.startTime)
    : ''

  if (!values.noEnd) {
    const endsLocal = joinLocal(values.endDate || values.startDate, values.endTime)
    if (!values.endDate.trim() && !values.startDate.trim()) {
      errors.ends = MSG_ENDS_REQUIRED
    } else if (!endsLocal) {
      errors.ends = MSG_ENDS_REQUIRED
    } else if (startsLocal) {
      const startsMs = new Date(startsLocal).getTime()
      const endsMs = new Date(endsLocal).getTime()
      if (!Number.isFinite(startsMs) || !Number.isFinite(endsMs) || endsMs <= startsMs) {
        errors.ends = MSG_END_AFTER_START
      }
    }
  }

  if (values.guestSubs.length < 1) {
    errors.attendees = MSG_ATTENDEES_REQUIRED
  }

  return errors
}

/**
 * Сопоставляет текст ошибки API с полем формы (для подсветки).
 * Неизвестные сообщения — общий баннер внутри модалки (`null`).
 */
export function calendarEventApiErrorField(message: string): CalendarEventFieldKey | null {
  const lower = message.toLowerCase()
  if (lower.includes('позже начала') || lower.includes('окончание')) {
    return 'ends'
  }
  if (lower.includes('участник')) {
    return 'attendees'
  }
  if (lower.includes('начал')) {
    return 'starts'
  }
  if (lower.includes('назван')) {
    return 'title'
  }
  if (lower.includes('календар')) {
    return 'calendar'
  }
  return null
}
