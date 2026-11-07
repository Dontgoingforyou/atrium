import { describe, expect, it } from 'vitest'

import {
  MSG_ATTENDEES_REQUIRED,
  MSG_CALENDAR_REQUIRED,
  MSG_END_AFTER_START,
  MSG_ENDS_REQUIRED,
  MSG_STARTS_REQUIRED,
  MSG_TITLE_REQUIRED,
  calendarEventApiErrorField,
  validateCalendarEventForm,
} from '../../../src/pages/calendar/calendarEventFormValidation'

const valid = {
  title: 'Дейлик',
  calendarId: 'cal-1',
  startDate: '2026-07-28',
  startTime: '10:00',
  endDate: '2026-07-28',
  endTime: '11:00',
  noEnd: false,
  guestSubs: ['user-1'],
}

describe('validateCalendarEventForm', () => {
  it('принимает валидную форму', () => {
    expect(validateCalendarEventForm(valid)).toEqual({})
  })

  it('требует название, календарь и начало', () => {
    expect(
      validateCalendarEventForm({
        ...valid,
        title: '  ',
        calendarId: '',
        startDate: '',
      }),
    ).toEqual({
      title: MSG_TITLE_REQUIRED,
      calendar: MSG_CALENDAR_REQUIRED,
      starts: MSG_STARTS_REQUIRED,
    })
  })

  it('требует хотя бы одного участника', () => {
    expect(
      validateCalendarEventForm({
        ...valid,
        guestSubs: [],
      }),
    ).toEqual({ attendees: MSG_ATTENDEES_REQUIRED })
  })

  it('требует окончание, если не «Без окончания»', () => {
    expect(
      validateCalendarEventForm({
        ...valid,
        endDate: '',
        startDate: '',
        endTime: '',
        noEnd: false,
      }),
    ).toMatchObject({
      starts: MSG_STARTS_REQUIRED,
      ends: MSG_ENDS_REQUIRED,
    })
  })

  it('отклоняет окончание раньше или равное началу', () => {
    expect(
      validateCalendarEventForm({
        ...valid,
        startTime: '17:30',
        endTime: '11:00',
      }),
    ).toEqual({ ends: MSG_END_AFTER_START })

    expect(
      validateCalendarEventForm({
        ...valid,
        endTime: '10:00',
      }),
    ).toEqual({ ends: MSG_END_AFTER_START })
  })

  it('пропускает окончание при «Без окончания»', () => {
    expect(
      validateCalendarEventForm({
        ...valid,
        noEnd: true,
        endTime: '09:00',
      }),
    ).toEqual({})
  })
})

describe('calendarEventApiErrorField', () => {
  it('мапит ошибку окончания на поле ends', () => {
    expect(calendarEventApiErrorField('Окончание события должно быть позже начала')).toBe('ends')
  })

  it('мапит ошибку участников', () => {
    expect(calendarEventApiErrorField('Укажите хотя бы одного участника')).toBe('attendees')
  })

  it('возвращает null для общего сообщения', () => {
    expect(calendarEventApiErrorField('Недостаточно прав для этого действия.')).toBeNull()
  })
})
