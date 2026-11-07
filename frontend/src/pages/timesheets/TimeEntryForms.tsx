import { useState, type Dispatch, type FormEvent, type ReactNode, type SetStateAction } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { isApiConflictError } from '../../api/apiConflict'
import {
  PORTAL_TIME_ENTRIES_REPORT_ROOT_QUERY_KEY,
  PORTAL_TIME_ENTRIES_ROOT_QUERY_KEY,
  PORTAL_TIME_ENTRIES_SUMMARY_ROOT_QUERY_KEY,
} from '../../api/queryKeys'
import { createTimeEntry, patchTimeEntry } from '../../api/timeEntries/timeEntriesApi'
import type { PortalTimeEntry, TimeEntryCreate, TimeEntryPatch } from '../../types/timeEntry'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { useNotifyToast } from '../../hooks/useNotifyToast'
import {
  buildDuplicateTimeEntryCreate,
  parseHoursToMinutes,
  todayStr,
} from '@/utils/time/timeEntryUtils'
import shared from '@/styles/modules/timesheets/TimesheetsPageShared.module.css'
import panels from '@/styles/modules/timesheets/TimesheetsPagePanels.module.css'

const HOURS_RANGE_ERROR = 'Укажите время от 1 минуты до 24 часов'

type FieldValues = {
  workedOn: string
  hours: string
  taskName: string
  note: string
}

function DateHoursFields({
  values,
  onChange,
  dateLabel,
}: {
  values: FieldValues
  onChange: (patch: Partial<FieldValues>) => void
  dateLabel: string
}) {
  return (
    <>
      <label className="form-label">
        <span className="form-label-text">{dateLabel}</span>
        <input
          type="date"
          value={values.workedOn}
          onChange={(e) => onChange({ workedOn: e.target.value })}
          className="form-input"
        />
      </label>
      <label className="form-label">
        <span className="form-label-text">Часы</span>
        <input
          type="number"
          value={values.hours}
          min={0.5}
          max={24}
          step={0.5}
          onChange={(e) => onChange({ hours: e.target.value })}
          className={`form-input ${panels.hoursInput}`}
        />
      </label>
    </>
  )
}

function TaskNoteFields({
  values,
  onChange,
  flex,
}: {
  values: FieldValues
  onChange: (patch: Partial<FieldValues>) => void
  flex?: boolean
}) {
  const cls = flex ? `form-label ${panels.formFieldFlex}` : 'form-label'
  return (
    <>
      <label className={cls}>
        <span className="form-label-text">Задача</span>
        <input
          type="text"
          value={values.taskName}
          onChange={(e) => onChange({ taskName: e.target.value })}
          placeholder="Название задачи"
          className="form-input"
        />
      </label>
      <label className={cls}>
        <span className="form-label-text">Описание задачи</span>
        <input
          type="text"
          value={values.note}
          onChange={(e) => onChange({ note: e.target.value })}
          placeholder="Что делали…"
          className="form-input"
        />
      </label>
    </>
  )
}

function validateEntryFields(
  values: FieldValues,
  setFormError: (msg: string) => void,
): number | null {
  const totalMinutes = parseHoursToMinutes(values.hours)
  if (totalMinutes === null) {
    setFormError(HOURS_RANGE_ERROR)
    return null
  }
  if (!values.workedOn) {
    setFormError('Укажите дату')
    return null
  }
  return totalMinutes
}

function patchValues(
  setValues: Dispatch<SetStateAction<FieldValues>>,
): (patch: Partial<FieldValues>) => void {
  return (patch) => setValues((prev) => ({ ...prev, ...patch }))
}

export function CreateEntryForm({ onCreated }: { onCreated: () => void }) {
  const [values, setValues] = useState<FieldValues>({
    workedOn: todayStr(),
    hours: '1',
    taskName: '',
    note: '',
  })
  const [formError, setFormError] = useState('')
  const onChange = patchValues(setValues)

  const mutation = useMutation({
    mutationFn: (body: TimeEntryCreate) => createTimeEntry(body),
    onSuccess: () => {
      setValues({ workedOn: todayStr(), hours: '1', taskName: '', note: '' })
      setFormError('')
      onCreated()
    },
    onError: (e: unknown) => setFormError(userFacingMessageFromUnknown(e)),
  })

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const totalMinutes = validateEntryFields(values, setFormError)
    if (totalMinutes === null) return
    mutation.mutate({
      worked_on: values.workedOn,
      minutes: totalMinutes,
      task_name: values.taskName.trim() || null,
      note: values.note.trim() || null,
    })
  }

  return (
    <form onSubmit={handleSubmit} noValidate className={`form-panel ${panels.createEntryForm}`}>
      <h3 className="form-panel-title">Новая запись</h3>
      <div className={panels.formRow}>
        <DateHoursFields values={values} onChange={onChange} dateLabel="Дата *" />
      </div>
      <p className={panels.hoursHint}>
        Шаг 0.5 ч — для быстрого ввода стрелочками. Можно ввести и точнее, например{' '}
        <code>0.25</code> = 15 мин; округление до получаса — это нормально.
      </p>
      <TaskNoteFields values={values} onChange={onChange} />
      {formError ? <p className="form-error">{formError}</p> : null}
      <button
        type="submit"
        disabled={mutation.isPending}
        className={`btn-primary ${panels.btnSubmitEntry}`}
      >
        {mutation.isPending ? 'Сохранение…' : 'Добавить'}
      </button>
    </form>
  )
}

function InlineEntryFormShell({
  children,
  formError,
}: {
  children: ReactNode
  formError: string
}) {
  return (
    <div className={`${shared.entryRow} ${panels.entryRowEditing}`}>
      {children}
      {formError ? <p className="form-error">{formError}</p> : null}
    </div>
  )
}

export function EditEntryForm({
  entry,
  onDone,
  onCancel,
}: {
  entry: PortalTimeEntry
  onDone: () => void
  onCancel: () => void
}) {
  const qc = useQueryClient()
  const notifyToast = useNotifyToast()
  const [values, setValues] = useState<FieldValues>({
    workedOn: entry.worked_on,
    hours: String(entry.minutes / 60),
    taskName: entry.task_name ?? '',
    note: entry.note ?? '',
  })
  const [formError, setFormError] = useState('')
  const onChange = patchValues(setValues)

  const mutation = useMutation({
    mutationFn: (body: TimeEntryPatch) => patchTimeEntry(entry.id, body),
    onSuccess: onDone,
    onError: (e: unknown) => {
      const message = userFacingMessageFromUnknown(e)
      setFormError(message)
      if (isApiConflictError(e)) {
        notifyToast(message)
        void qc.invalidateQueries({ queryKey: PORTAL_TIME_ENTRIES_ROOT_QUERY_KEY })
        void qc.invalidateQueries({ queryKey: PORTAL_TIME_ENTRIES_SUMMARY_ROOT_QUERY_KEY })
        void qc.invalidateQueries({ queryKey: PORTAL_TIME_ENTRIES_REPORT_ROOT_QUERY_KEY })
      }
    },
  })

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const totalMinutes = validateEntryFields(values, setFormError)
    if (totalMinutes === null) return
    mutation.mutate({
      expected_version: entry.version,
      worked_on: values.workedOn,
      minutes: totalMinutes,
      task_name: values.taskName.trim() || null,
      note: values.note.trim() || null,
    })
  }

  return (
    <InlineEntryFormShell formError={formError}>
      <form onSubmit={handleSubmit} noValidate className={shared.inlineForm}>
        <DateHoursFields values={values} onChange={onChange} dateLabel="Дата" />
        <TaskNoteFields values={values} onChange={onChange} flex />
        <div className={panels.inlineFormActions}>
          <button type="submit" disabled={mutation.isPending} className="btn-primary">
            {mutation.isPending ? 'Сохранение…' : 'Сохранить'}
          </button>
          <button type="button" onClick={onCancel} className={shared.editBtn}>
            Отмена
          </button>
        </div>
      </form>
    </InlineEntryFormShell>
  )
}

export function DuplicateEntryForm({
  entry,
  onDone,
  onCancel,
}: {
  entry: PortalTimeEntry
  onDone: () => void
  onCancel: () => void
}) {
  const [values, setValues] = useState<FieldValues>({
    workedOn: todayStr(),
    hours: String(entry.minutes / 60),
    taskName: entry.task_name ?? '',
    note: entry.note ?? '',
  })
  const [formError, setFormError] = useState('')
  const onChange = patchValues(setValues)

  const mutation = useMutation({
    mutationFn: (body: TimeEntryCreate) => createTimeEntry(body),
    onSuccess: onDone,
    onError: (e: unknown) => setFormError(userFacingMessageFromUnknown(e)),
  })

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const totalMinutes = validateEntryFields(values, setFormError)
    if (totalMinutes === null) return
    mutation.mutate(
      buildDuplicateTimeEntryCreate(entry, {
        worked_on: values.workedOn,
        minutes: totalMinutes,
        task_name: values.taskName,
        note: values.note,
      }),
    )
  }

  return (
    <InlineEntryFormShell formError={formError}>
      <form onSubmit={handleSubmit} noValidate className={shared.inlineForm}>
        <DateHoursFields values={values} onChange={onChange} dateLabel="Дата" />
        <TaskNoteFields values={values} onChange={onChange} flex />
        <div className={panels.inlineFormActions}>
          <button type="submit" disabled={mutation.isPending} className="btn-primary">
            {mutation.isPending ? 'Создание…' : 'Создать копию'}
          </button>
          <button type="button" onClick={onCancel} className={shared.editBtn}>
            Отмена
          </button>
        </div>
      </form>
    </InlineEntryFormShell>
  )
}
