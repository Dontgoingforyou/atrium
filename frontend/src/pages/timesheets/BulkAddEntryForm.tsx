import { useMemo, useState, type FormEvent } from 'react'
import { useMutation } from '@tanstack/react-query'
import { createTimeEntriesBulk } from '../../api/timeEntries/timeEntriesApi'
import type { TimeEntryBulkCreate } from '../../types/timeEntry'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import {
  DEFAULT_BULK_WEEKDAYS,
  generateWeekdayDates,
  parseHoursToMinutes,
  todayStr,
  WEEKDAY_LABELS_SHORT,
} from '@/utils/time/timeEntryUtils'
import panels from '@/styles/modules/timesheets/TimesheetsPagePanels.module.css'

export function BulkAddEntryForm({
  onCreated,
  onCancel,
}: {
  onCreated: (count: number) => void
  onCancel: () => void
}) {
  const [dateFrom, setDateFrom] = useState(todayStr())
  const [dateTo, setDateTo] = useState(todayStr())
  const [weekdays, setWeekdays] = useState<number[]>(DEFAULT_BULK_WEEKDAYS)
  const [hours, setHours] = useState('1')
  const [taskName, setTaskName] = useState('')
  const [note, setNote] = useState('')
  const [formError, setFormError] = useState('')

  const previewDates = useMemo(
    () => generateWeekdayDates(dateFrom, dateTo, weekdays),
    [dateFrom, dateTo, weekdays],
  )

  const mutation = useMutation({
    mutationFn: (body: TimeEntryBulkCreate) => createTimeEntriesBulk(body),
    onSuccess: (rows) => onCreated(rows.length),
    onError: (e: unknown) => setFormError(userFacingMessageFromUnknown(e)),
  })

  function toggleWeekday(day: number) {
    setWeekdays((prev) => (prev.includes(day) ? prev.filter((d) => d !== day) : [...prev, day].sort()))
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const totalMinutes = parseHoursToMinutes(hours)
    if (totalMinutes === null) {
      setFormError('Укажите время от 1 минуты до 24 часов')
      return
    }
    if (!dateFrom || !dateTo) {
      setFormError('Укажите диапазон дат')
      return
    }
    if (dateTo < dateFrom) {
      setFormError('Дата «по» не может быть раньше даты «с»')
      return
    }
    if (weekdays.length === 0) {
      setFormError('Отметьте хотя бы один день недели')
      return
    }
    if (previewDates.length === 0) {
      setFormError('В выбранном диапазоне нет дат с указанными днями недели')
      return
    }
    mutation.mutate({
      date_from: dateFrom,
      date_to: dateTo,
      weekdays,
      minutes: totalMinutes,
      task_name: taskName.trim() || null,
      note: note.trim() || null,
    })
  }

  return (
    <form onSubmit={handleSubmit} noValidate className={`form-panel ${panels.createEntryForm}`}>
      <h3 className="form-panel-title">Массовое добавление</h3>
      <div className={panels.formRow}>
        <label className="form-label">
          <span className="form-label-text">Дата с *</span>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="form-input"
          />
        </label>
        <label className="form-label">
          <span className="form-label-text">Дата по *</span>
          <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="form-input" />
        </label>
        <label className="form-label">
          <span className="form-label-text">Часы</span>
          <input
            type="number"
            value={hours}
            min={0.5}
            max={24}
            step={0.5}
            onChange={(e) => setHours(e.target.value)}
            className={`form-input ${panels.hoursInput}`}
          />
        </label>
      </div>

      <div className="form-label">
        <span className="form-label-text">Дни недели</span>
        <div className={panels.weekdayPicker}>
          {WEEKDAY_LABELS_SHORT.map((label, day) => {
            const checked = weekdays.includes(day)
            return (
              <label
                key={day}
                className={`${panels.weekdayOption} ${checked ? panels.weekdayOptionChecked : ''}`}
              >
                <input type="checkbox" checked={checked} onChange={() => toggleWeekday(day)} />
                {label}
              </label>
            )
          })}
        </div>
      </div>

      <label className="form-label">
        <span className="form-label-text">Задача</span>
        <input
          type="text"
          value={taskName}
          onChange={(e) => setTaskName(e.target.value)}
          placeholder="Название задачи"
          className="form-input"
        />
      </label>
      <label className="form-label">
        <span className="form-label-text">Описание задачи</span>
        <input
          type="text"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Что делали…"
          className="form-input"
        />
      </label>

      <p className={panels.bulkPreview}>
        {previewDates.length > 0
          ? `Будет создано записей: ${previewDates.length}`
          : 'Нет дат, подходящих под выбранный диапазон и дни недели'}
      </p>

      {formError ? <p className="form-error">{formError}</p> : null}
      <div className={panels.inlineFormActions}>
        <button
          type="submit"
          disabled={mutation.isPending || previewDates.length === 0}
          className={`btn-primary ${panels.btnSubmitEntry}`}
        >
          {mutation.isPending ? 'Создание…' : 'Создать записи'}
        </button>
        <button type="button" onClick={onCancel} className="btn-secondary">
          Отмена
        </button>
      </div>
    </form>
  )
}
