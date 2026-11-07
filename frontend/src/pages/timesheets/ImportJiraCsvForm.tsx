import { useRef, useState, type FormEvent } from 'react'
import { useMutation } from '@tanstack/react-query'
import { importJiraTimeEntriesCsv } from '../../api/timeEntries/timeEntriesApi'
import type { TimeEntryImportResult } from '../../types/timeEntry'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import panels from '@/styles/modules/timesheets/TimesheetsPagePanels.module.css'

export function ImportJiraCsvForm({
  onImported,
  onCancel,
}: {
  onImported: (result: TimeEntryImportResult) => void
  onCancel: () => void
}) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [formError, setFormError] = useState('')

  const mutation = useMutation({
    mutationFn: (file: File) => importJiraTimeEntriesCsv(file),
    onSuccess: (result) => {
      setSelectedFile(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
      onImported(result)
    },
    onError: (e: unknown) => setFormError(userFacingMessageFromUnknown(e)),
  })

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!selectedFile) {
      setFormError('Выберите CSV-файл выгрузки Jira')
      return
    }
    setFormError('')
    mutation.mutate(selectedFile)
  }

  return (
    <form onSubmit={handleSubmit} noValidate className={`form-panel ${panels.createEntryForm}`}>
      <h3 className="form-panel-title">Импорт из Jira</h3>
      <p className={panels.bulkPreview}>
        CSV-выгрузка Jira Tempo (worklog): используются только колонки «Тема задачи», «Дата работы» и «Часов». Каждая
        строка становится отдельной записью таймшита от вашего имени.
      </p>

      <label className="form-label">
        <span className="form-label-text">Файл (.csv)</span>
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,text/csv"
          onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
          className="form-input"
        />
      </label>

      {formError ? <p className="form-error">{formError}</p> : null}
      <div className={panels.inlineFormActions}>
        <button
          type="submit"
          disabled={mutation.isPending || !selectedFile}
          className={`btn-primary ${panels.btnSubmitEntry}`}
        >
          {mutation.isPending ? 'Импорт…' : 'Импортировать'}
        </button>
        <button type="button" onClick={onCancel} className="btn-secondary">
          Отмена
        </button>
      </div>
    </form>
  )
}
