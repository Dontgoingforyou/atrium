import { type FormEvent, useState } from 'react'

import { DayCalendarPicker } from '../../components/common/DayCalendarPicker'
import { TimePicker } from '../../components/common/TimePicker'
import { UserMultiPicker } from '../../components/common/UserMultiPicker'
import { Modal } from '../../components/ui/Modal'
import {
  CALENDAR_MAX_REMINDERS,
  CALENDAR_REMINDER_OFFSET_PRESETS,
  DEFAULT_REMINDER_OFFSET_MINUTES,
  reminderOffsetLabelRu,
} from '../../domain/calendar/calendarReminderPresets'
import {
  presetFromRrule,
  rruleFromPreset,
  type RrulePreset,
} from '../../domain/calendar/calendarRrule'
import {
  DEFAULT_CALENDAR_COLOR,
  toColorInputValue,
} from '../../domain/calendar/calendarColor'
import {
  buildCalendarEventDirtyPatch,
  isCalendarEventDirtyPatchEmpty,
  type CalendarEventDirtyPatch,
  type CalendarEventFormSnapshot,
} from '../../domain/calendar/calendarEventDirtyPatch'
import {
  initialGuestSubs,
  initialReminderOffsets,
} from '../../domain/calendar/calendarEventFormInit'
import {
  joinLocal,
  plusOneHourLocal,
  splitLocal,
  toLocalFromIso,
} from '../../domain/calendar/calendarLocalTime'
import { useAuthStore } from '../../store/authStore'
import type {
  CalendarEventCreate,
  PortalCalendar,
  PortalCalendarOccurrence,
} from '../../types/calendar'
import dayPickerStyles from '@/styles/modules/common/DayCalendarPicker.module.css'
import styles from '@/styles/modules/calendar/CalendarPage.module.css'
import {
  calendarEventApiErrorField,
  type CalendarEventFieldErrors,
  validateCalendarEventForm,
} from './calendarEventFormValidation'

/** Payload формы события = API create-body без timezone (по умолчанию UTC на бэкенде). */
export type CalendarEventFormPayload = Omit<CalendarEventCreate, 'timezone'>

function localToIso(local: string): string {
  if (!local) return ''
  const parsed = new Date(local)
  return Number.isNaN(parsed.getTime()) ? '' : parsed.toISOString()
}

type Props = {
  calendars: PortalCalendar[]
  initialCalendarId: string
  startsLocal: string
  endsLocal: string
  pending: boolean
  mode?: 'create' | 'edit'
  initialOccurrence?: PortalCalendarOccurrence | null
  /** Ошибка мутации API — показывается в модалке (и подсвечивает поле, если удаётся сопоставить). */
  submitError?: string | null
  /** Режим онбординга: форма только для показа, без сохранения. */
  tourDemo?: boolean
  onClearSubmitError?: () => void
  /** sub коллеги, в чей календарь создаём событие (peer-view). */
  peerCreateForSub?: string | null
  peerCalendarLabel?: string | null
  onClose: () => void
  onSubmit?: (payload: CalendarEventFormPayload) => void
  /** Edit: только изменённые поля. Пустой набор закрывает модалку без PATCH. */
  onSubmitEdit?: (patch: CalendarEventDirtyPatch) => void
}

export function CalendarEventFormModal({
  calendars,
  initialCalendarId,
  startsLocal: initialStarts,
  endsLocal: initialEnds,
  pending,
  mode = 'create',
  initialOccurrence = null,
  submitError = null,
  tourDemo = false,
  peerCreateForSub = null,
  peerCalendarLabel = null,
  onClearSubmitError,
  onClose,
  onSubmit,
  onSubmitEdit,
}: Props) {
  const currentSub = useAuthStore((s) => s.user?.sub)
  const startInit = splitLocal(
    initialOccurrence ? toLocalFromIso(initialOccurrence.starts_at) : initialStarts,
  )
  const endInitRaw = initialOccurrence
    ? initialOccurrence.ends_at
      ? toLocalFromIso(initialOccurrence.ends_at)
      : ''
    : initialEnds
  const endInit = endInitRaw ? splitLocal(endInitRaw) : { date: '', time: '11:00' }

  const [title, setTitle] = useState(initialOccurrence?.title ?? '')
  const [location, setLocation] = useState(initialOccurrence?.location ?? '')
  const [description, setDescription] = useState(initialOccurrence?.description ?? '')
  const [startDate, setStartDate] = useState(startInit.date)
  const [startTime, setStartTime] = useState(startInit.time)
  const [endDate, setEndDate] = useState(endInit.date)
  const [endTime, setEndTime] = useState(endInit.time)
  const [noEnd, setNoEnd] = useState(
    initialOccurrence ? initialOccurrence.ends_at == null : !initialEnds,
  )
  const [calendarId, setCalendarId] = useState(
    initialOccurrence?.calendar_id ?? initialCalendarId,
  )
  const [rrulePreset, setRrulePreset] = useState<RrulePreset>(() =>
    presetFromRrule(initialOccurrence?.rrule),
  )
  const [guestSubs, setGuestSubs] = useState<string[]>(() =>
    initialGuestSubs(mode, currentSub, initialOccurrence, peerCreateForSub),
  )
  const [reminderOffsets, setReminderOffsets] = useState<number[]>(() =>
    initialReminderOffsets(initialOccurrence),
  )
  const [eventColor, setEventColor] = useState(
    () =>
      initialOccurrence?.color ??
      calendars.find((c) => c.id === (initialOccurrence?.calendar_id ?? initialCalendarId))?.color ??
      DEFAULT_CALENDAR_COLOR,
  )
  const [fieldErrors, setFieldErrors] = useState<CalendarEventFieldErrors>({})
  const [openSnapshot] = useState<CalendarEventFormSnapshot | null>(() => {
    if (mode !== 'edit') return null
    const startsJoined = joinLocal(startInit.date, startInit.time)
    const endsJoined = noEnd ? '' : joinLocal(endInit.date || startInit.date, endInit.time)
    return {
      title: title.trim(),
      description: description.trim() || null,
      location: location.trim() || null,
      starts_at: localToIso(startsJoined),
      ends_at: noEnd ? null : localToIso(endsJoined),
      rrule: rruleFromPreset(rrulePreset),
      color: eventColor,
      attendees: guestSubs.map((user_sub) => ({ user_sub })),
      reminders: reminderOffsets.map((offset_minutes) => ({ offset_minutes })),
    }
  })

  const selectedCalendarColor =
    calendars.find((c) => c.id === calendarId)?.color ?? DEFAULT_CALENDAR_COLOR

  const lockedSubs = peerCreateForSub ? [] : currentSub ? [currentSub] : []
  const isPeerCreate = Boolean(peerCreateForSub && mode === 'create')

  const apiField = submitError ? calendarEventApiErrorField(submitError) : null
  const titleInvalid = Boolean(fieldErrors.title || apiField === 'title')
  const calendarInvalid = Boolean(fieldErrors.calendar || apiField === 'calendar')
  const startsInvalid = Boolean(fieldErrors.starts || apiField === 'starts')
  const endsError = fieldErrors.ends ?? (apiField === 'ends' ? submitError : null)
  const endsInvalid = Boolean(endsError)
  const attendeesError =
    fieldErrors.attendees ?? (apiField === 'attendees' ? submitError : null)
  const attendeesInvalid = Boolean(attendeesError)
  const titleMsg = fieldErrors.title ?? (apiField === 'title' ? submitError : null)
  const calendarMsg = fieldErrors.calendar ?? (apiField === 'calendar' ? submitError : null)
  const startsMsg = fieldErrors.starts ?? (apiField === 'starts' ? submitError : null)
  const generalError = submitError && !apiField ? submitError : null

  function formValues() {
    return {
      title,
      calendarId,
      startDate,
      startTime,
      endDate,
      endTime,
      noEnd,
      guestSubs,
    }
  }

  function revalidateFields(next: Partial<ReturnType<typeof formValues>> = {}) {
    const merged = { ...formValues(), ...next }
    const nextErrors = validateCalendarEventForm(merged)
    setFieldErrors(nextErrors)
    onClearSubmitError?.()
  }

  function clearFieldError(key: keyof CalendarEventFieldErrors) {
    if (fieldErrors[key]) {
      setFieldErrors((prev) => {
        const copy = { ...prev }
        delete copy[key]
        return copy
      })
    }
    onClearSubmitError?.()
  }

  function formSnapshot(): CalendarEventFormSnapshot {
    const startsLocal = joinLocal(startDate, startTime)
    const endsLocal = noEnd ? '' : joinLocal(endDate || startDate, endTime)
    return {
      title: title.trim(),
      description: description.trim() || null,
      location: location.trim() || null,
      starts_at: localToIso(startsLocal),
      ends_at: noEnd ? null : localToIso(endsLocal),
      rrule: rruleFromPreset(rrulePreset),
      color: eventColor || selectedCalendarColor,
      attendees: guestSubs.map((user_sub) => ({ user_sub })),
      reminders: reminderOffsets.map((offset_minutes) => ({ offset_minutes })),
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (tourDemo) return
    const nextErrors = validateCalendarEventForm(formValues())
    setFieldErrors(nextErrors)
    onClearSubmitError?.()
    if (Object.keys(nextErrors).length > 0) return

    const current = formSnapshot()
    if (mode === 'edit' && onSubmitEdit) {
      const dirty = buildCalendarEventDirtyPatch(openSnapshot ?? current, current)
      if (isCalendarEventDirtyPatchEmpty(dirty)) {
        onClose()
        return
      }
      onSubmitEdit(dirty)
      return
    }
    onSubmit?.({
      calendar_id: calendarId,
      ...current,
    })
  }

  function addReminder() {
    if (reminderOffsets.length >= CALENDAR_MAX_REMINDERS) return
    setReminderOffsets((prev) => [...prev, DEFAULT_REMINDER_OFFSET_MINUTES])
  }

  function removeReminder(index: number) {
    setReminderOffsets((prev) => prev.filter((_, i) => i !== index))
  }

  function setReminderAt(index: number, offset: number) {
    setReminderOffsets((prev) => prev.map((v, i) => (i === index ? offset : v)))
  }

  return (
    <Modal title={mode === 'edit' ? 'Редактировать событие' : 'Новое событие'} onClose={onClose} maxWidth={480}>
      <form
        className={styles.modalForm}
        onSubmit={handleSubmit}
        noValidate
        data-tour={tourDemo ? 'calendar-event-edit-form' : undefined}
        {...(tourDemo ? { inert: true } : {})}
      >
        {generalError ? (
          <p className="form-error" role="alert">
            {generalError}
          </p>
        ) : null}
        <div className={styles.field}>
          <label htmlFor="cal-title">Название</label>
          <input
            id="cal-title"
            className={['form-input', titleInvalid ? 'form-input-invalid' : '']
              .filter(Boolean)
              .join(' ')}
            value={title}
            aria-invalid={titleInvalid || undefined}
            onChange={(e) => {
              setTitle(e.target.value)
              clearFieldError('title')
            }}
          />
          {titleMsg ? (
            <p className={styles.fieldError} role="alert">
              {titleMsg}
            </p>
          ) : null}
        </div>
        {mode === 'create' ? (
          <div className={styles.field}>
            <label htmlFor="cal-calendar">Календарь</label>
            {isPeerCreate ? (
              <p className="text-muted" id="cal-calendar">
                {peerCalendarLabel ?? 'Календарь участника'}
              </p>
            ) : (
              <select
                id="cal-calendar"
                className={['form-input', calendarInvalid ? 'form-input-invalid' : '']
                  .filter(Boolean)
                  .join(' ')}
                value={calendarId}
                aria-invalid={calendarInvalid || undefined}
                onChange={(e) => {
                  setCalendarId(e.target.value)
                  clearFieldError('calendar')
                }}
              >
                {calendars.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.title}
                  </option>
                ))}
              </select>
            )}
            {calendarMsg ? (
              <p className={styles.fieldError} role="alert">
                {calendarMsg}
              </p>
            ) : null}
          </div>
        ) : null}
        <div className={styles.field}>
          <span className={styles.fieldLabel}>Начало</span>
          <div className={styles.dateTimeRow}>
            <DayCalendarPicker
              label=""
              value={startDate}
              onChange={(next) => {
                setStartDate(next)
                if (noEnd) {
                  revalidateFields({ startDate: next })
                  return
                }
                if (mode === 'create') {
                  const end = plusOneHourLocal(next, startTime)
                  setEndDate(end.date)
                  setEndTime(end.time)
                  revalidateFields({ startDate: next, endDate: end.date, endTime: end.time })
                  return
                }
                setEndDate(next)
                const [sh, sm] = startTime.split(':').map(Number)
                const [eh, em] = endTime.split(':').map(Number)
                const startMins = (sh ?? 0) * 60 + (sm ?? 0)
                const endMins = (eh ?? 0) * 60 + (em ?? 0)
                let nextEndTime = endTime
                if (endMins <= startMins) {
                  const bumped = Math.min(startMins + 60, 23 * 60 + 59)
                  const pad = (n: number) => String(n).padStart(2, '0')
                  nextEndTime = `${pad(Math.floor(bumped / 60))}:${pad(bumped % 60)}`
                  setEndTime(nextEndTime)
                }
                revalidateFields({ startDate: next, endDate: next, endTime: nextEndTime })
              }}
              allowClear={false}
              placeholder="Дата"
              invalid={startsInvalid}
              className={`${dayPickerStyles.fixedWidth} ${styles.dayPicker}`}
            />
            <TimePicker
              value={startTime}
              onChange={(next) => {
                setStartTime(next)
                if (mode === 'create' && !noEnd && startDate) {
                  const end = plusOneHourLocal(startDate, next)
                  setEndDate(end.date)
                  setEndTime(end.time)
                  revalidateFields({ startTime: next, endDate: end.date, endTime: end.time })
                  return
                }
                revalidateFields({ startTime: next })
              }}
              aria-label="Время начала"
              invalid={startsInvalid}
              className={styles.timeInput}
            />
          </div>
          {startsMsg ? (
            <p className={styles.fieldError} role="alert">
              {startsMsg}
            </p>
          ) : null}
        </div>
        <div className={styles.field}>
          <span className={styles.fieldLabel}>Окончание</span>
          <label className={styles.checkRow}>
            <input
              type="checkbox"
              checked={noEnd}
              onChange={(e) => {
                const next = e.target.checked
                setNoEnd(next)
                revalidateFields({ noEnd: next })
              }}
            />
            Без окончания
          </label>
          {!noEnd ? (
            <div className={styles.dateTimeRow}>
              <DayCalendarPicker
                label=""
                value={endDate || startDate}
                onChange={(next) => {
                  setEndDate(next)
                  revalidateFields({ endDate: next })
                }}
                allowClear={false}
                placeholder="Дата"
                invalid={endsInvalid}
                className={`${dayPickerStyles.fixedWidth} ${styles.dayPicker}`}
              />
              <TimePicker
                value={endTime}
                onChange={(next) => {
                  setEndTime(next)
                  revalidateFields({ endTime: next })
                }}
                aria-label="Время окончания"
                invalid={endsInvalid}
                className={styles.timeInput}
              />
            </div>
          ) : null}
          {endsError ? (
            <p className={styles.fieldError} role="alert">
              {endsError}
            </p>
          ) : null}
        </div>
        <div className={styles.field}>
          <label htmlFor="cal-loc">Место</label>
          <input
            id="cal-loc"
            className="form-input"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
          />
        </div>
        <div className={styles.field}>
          <label htmlFor="cal-desc">Описание</label>
          <textarea
            id="cal-desc"
            className="form-input"
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
        <div className={styles.field}>
          <label htmlFor="cal-rrule">Повтор</label>
          <select
            id="cal-rrule"
            className="form-input"
            value={rrulePreset}
            onChange={(e) => setRrulePreset(e.target.value as RrulePreset)}
          >
            <option value="none">Без повтора</option>
            <option value="daily">Каждый день</option>
            <option value="weekdays">По будням</option>
            <option value="weekly">Раз в неделю</option>
            <option value="monthly">Раз в месяц</option>
          </select>
        </div>
        <div className={styles.field}>
          <span className={styles.fieldLabel}>Цвет события</span>
          <div className={styles.eventColorRow} role="group" aria-label="Цвет события">
            <label
              className={[styles.calColorSwatch, styles.eventColorPickerWrap, styles.eventColorSelected]
                .filter(Boolean)
                .join(' ')}
              style={{ background: eventColor || selectedCalendarColor }}
              title={`Цвет ${eventColor || selectedCalendarColor}`}
            >
              <input
                type="color"
                className={styles.calColorInput}
                value={toColorInputValue(eventColor || selectedCalendarColor)}
                onChange={(e) => setEventColor(e.target.value.toUpperCase())}
                aria-label="Цвет события"
              />
            </label>
          </div>
        </div>
        <div className={styles.field}>
          <span className={styles.fieldLabel}>Участники</span>
          <UserMultiPicker
            value={guestSubs}
            onChange={(next) => {
              const withSelf =
                currentSub && !next.includes(currentSub) ? [currentSub, ...next] : next
              setGuestSubs(withSelf)
              revalidateFields({ guestSubs: withSelf })
            }}
            placeholder="Добавить участников…"
            lockedValues={lockedSubs}
            invalid={attendeesInvalid}
          />
          {attendeesError ? (
            <p className={styles.fieldError} role="alert">
              {attendeesError}
            </p>
          ) : null}
        </div>
        <div className={styles.field}>
          <span className={styles.fieldLabel}>Напоминания</span>
          <ul className={styles.reminderList}>
            {reminderOffsets.map((offset, index) => (
              <li key={`rem-${index}`} className={styles.reminderRow}>
                <select
                  className="form-input"
                  value={offset}
                  aria-label={`Напоминание ${index + 1}`}
                  onChange={(e) => setReminderAt(index, Number(e.target.value))}
                >
                  {CALENDAR_REMINDER_OFFSET_PRESETS.map((preset) => (
                    <option key={preset} value={preset}>
                      {reminderOffsetLabelRu(preset)}
                    </option>
                  ))}
                  {!CALENDAR_REMINDER_OFFSET_PRESETS.includes(
                    offset as (typeof CALENDAR_REMINDER_OFFSET_PRESETS)[number],
                  ) ? (
                    <option value={offset}>{reminderOffsetLabelRu(offset)}</option>
                  ) : null}
                </select>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => removeReminder(index)}
                  disabled={reminderOffsets.length <= 1}
                  aria-label="Убрать напоминание"
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
          <button
            type="button"
            className="btn-secondary"
            onClick={addReminder}
            disabled={reminderOffsets.length >= CALENDAR_MAX_REMINDERS}
          >
            Добавить напоминание
          </button>
        </div>
        <div className={styles.actions}>
          <button type="button" className="btn-secondary" onClick={onClose}>
            Отмена
          </button>
          <button type="submit" className="btn-primary" disabled={pending}>
            {pending ? 'Сохранение…' : mode === 'edit' ? 'Сохранить' : 'Создать'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
