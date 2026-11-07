import { useState } from 'react'
import type { PortalTimeEntry } from '../../types/timeEntry'
import { formatMinutes } from '@/utils/time/timeEntryUtils'
import { DuplicateEntryForm, EditEntryForm } from './TimeEntryForms'
import shared from '@/styles/modules/timesheets/TimesheetsPageShared.module.css'

export function EntryRow({
  entry,
  onDelete,
  onUpdated,
}: {
  entry: PortalTimeEntry
  onDelete: () => void
  onUpdated: () => void
}) {
  const [mode, setMode] = useState<'view' | 'editing' | 'duplicating'>('view')

  if (mode === 'editing') {
    return (
      <EditEntryForm
        entry={entry}
        onDone={() => {
          setMode('view')
          onUpdated()
        }}
        onCancel={() => setMode('view')}
      />
    )
  }

  if (mode === 'duplicating') {
    return (
      <DuplicateEntryForm
        entry={entry}
        onDone={() => {
          setMode('view')
          onUpdated()
        }}
        onCancel={() => setMode('view')}
      />
    )
  }

  return (
    <div className={shared.entryRow}>
      <div className={shared.entryBody}>
        {entry.task_name ? (
          <div className={shared.entryTitle}>{entry.task_name}</div>
        ) : null}
        {entry.note ? (
          <div className={shared.entryNote}>{entry.note}</div>
        ) : !entry.task_name ? (
          <div className={shared.entryTitle}>—</div>
        ) : null}
        <div className={shared.entryMeta}>
          <span>{formatMinutes(entry.minutes)}</span>
        </div>
      </div>
      <div className={shared.entryActions}>
        <button type="button" onClick={() => setMode('editing')} className={shared.editBtn}>
          Изменить
        </button>
        <button type="button" onClick={() => setMode('duplicating')} className={shared.editBtn}>
          Дублировать
        </button>
        <button type="button" onClick={onDelete} className={shared.deleteBtn}>
          Удалить
        </button>
      </div>
    </div>
  )
}
