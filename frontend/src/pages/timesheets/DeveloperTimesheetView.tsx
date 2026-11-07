import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router'
import { deleteTimeEntry, getTimeEntrySummary, listTimeEntries } from '../../api/timeEntries/timeEntriesApi'
import {
  PORTAL_TIME_ENTRIES_REPORT_ROOT_QUERY_KEY,
  PORTAL_TIME_ENTRIES_ROOT_QUERY_KEY,
  PORTAL_TIME_ENTRIES_SUMMARY_ROOT_QUERY_KEY,
  timeEntriesQueryKey,
  timeEntriesSummaryQueryKey,
} from '../../api/queryKeys'
import type { TimeEntryImportResult } from '../../types/timeEntry'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { useNotifyToast } from '../../hooks/useNotifyToast'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import { TimeEntriesReportPanel } from './TimeEntriesReportPanel'
import { CreateEntryForm } from './TimeEntryForms'
import { BulkAddEntryForm } from './BulkAddEntryForm'
import { ImportJiraCsvForm } from './ImportJiraCsvForm'
import { DayGroupSection } from './DayGroupSection'
import { EntryRow } from './EntryRow'
import { formatMinutes, groupEntriesByDay } from '@/utils/time/timeEntryUtils'
import shared from '@/styles/modules/timesheets/TimesheetsPageShared.module.css'
import panels from '@/styles/modules/timesheets/TimesheetsPagePanels.module.css'

type Tab = 'entries' | 'report'

const ENTRIES_LIST_LIMIT = 200

export function DeveloperTimesheetView() {
  const queryClient = useQueryClient()
  const notify = useNotifyToast()
  const [searchParams, setSearchParams] = useSearchParams()
  const tab: Tab = searchParams.get('tab') === 'report' ? 'report' : 'entries'
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [showBulkForm, setShowBulkForm] = useState(false)
  const [showImportForm, setShowImportForm] = useState(false)
  const [bulkSuccessMessage, setBulkSuccessMessage] = useState('')
  const [importResult, setImportResult] = useState<TimeEntryImportResult | null>(null)
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null)

  function selectTab(next: Tab) {
    setSearchParams(
      (prev) => {
        const params = new URLSearchParams(prev)
        if (next === 'report') {
          params.set('tab', 'report')
        } else {
          params.delete('tab')
        }
        return params
      },
      { replace: true },
    )
  }

  const {
    data: entriesPage,
    isPending,
    isError,
    error,
  } = useQuery({
    queryKey: timeEntriesQueryKey({ dateFrom, dateTo }),
    queryFn: () =>
      listTimeEntries({
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        limit: ENTRIES_LIST_LIMIT,
      }),
    enabled: tab === 'entries',
  })

  const entries = entriesPage?.items ?? []
  const entriesTotal = entriesPage?.total ?? 0
  const entriesTruncated = entries.length < entriesTotal
  const dayGroups = groupEntriesByDay(entries)

  const {
    data: summary,
    isPending: summaryPending,
    isError: summaryError,
    error: summaryErrorValue,
  } = useQuery({
    queryKey: timeEntriesSummaryQueryKey({ dateFrom, dateTo }),
    queryFn: () =>
      getTimeEntrySummary({
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      }),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteTimeEntry(id),
    onSuccess: () => {
      setDeleteConfirmId(null)
      invalidateAll()
    },
    onError: (e: unknown) => notify(userFacingMessageFromUnknown(e), { silent: true }),
  })

  function invalidateAll() {
    queryClient.invalidateQueries({ queryKey: PORTAL_TIME_ENTRIES_ROOT_QUERY_KEY })
    queryClient.invalidateQueries({ queryKey: PORTAL_TIME_ENTRIES_SUMMARY_ROOT_QUERY_KEY })
    queryClient.invalidateQueries({ queryKey: PORTAL_TIME_ENTRIES_REPORT_ROOT_QUERY_KEY })
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Таймшиты</h1>
        <div className={panels.headerActions} data-tour="analytics-timesheets-actions">
          <button
            type="button"
            onClick={() => {
              setShowImportForm((v) => !v)
              setShowForm(false)
              setShowBulkForm(false)
              setImportResult(null)
              selectTab('entries')
            }}
            className="btn-secondary"
          >
            {showImportForm ? 'Отмена' : 'Импорт из Jira'}
          </button>
          <button
            type="button"
            onClick={() => {
              setShowBulkForm((v) => !v)
              setShowForm(false)
              setShowImportForm(false)
              setBulkSuccessMessage('')
              selectTab('entries')
            }}
            className="btn-secondary"
          >
            {showBulkForm ? 'Отмена' : 'Массовое добавление'}
          </button>
          <button
            type="button"
            onClick={() => {
              setShowForm((v) => !v)
              setShowBulkForm(false)
              setShowImportForm(false)
              setBulkSuccessMessage('')
              selectTab('entries')
            }}
            className="btn-primary"
          >
            {showForm ? 'Отмена' : '+ Добавить запись'}
          </button>
        </div>
      </div>

      {showForm ? (
        <CreateEntryForm
          onCreated={() => {
            setShowForm(false)
            invalidateAll()
          }}
        />
      ) : null}

      {showBulkForm ? (
        <BulkAddEntryForm
          onCreated={(count) => {
            setShowBulkForm(false)
            setBulkSuccessMessage(`Создано записей: ${count}`)
            invalidateAll()
          }}
          onCancel={() => setShowBulkForm(false)}
        />
      ) : null}

      {showImportForm ? (
        <ImportJiraCsvForm
          onImported={(result) => {
            setShowImportForm(false)
            setImportResult(result)
            invalidateAll()
          }}
          onCancel={() => setShowImportForm(false)}
        />
      ) : null}

      {bulkSuccessMessage ? <p className={panels.bulkSuccess}>{bulkSuccessMessage}</p> : null}

      {importResult ? (
        <div className={panels.importSummary}>
          <p className={panels.importSummaryLine}>
            Импорт из Jira: создано записей — {importResult.created_count}
            {importResult.skipped_count > 0 ? `, пропущено — ${importResult.skipped_count}` : ''}
          </p>
          {importResult.errors.length > 0 ? (
            <ul className={panels.importErrorsList}>
              {importResult.errors.map((err) => (
                <li key={err.row} className={panels.importErrorItem}>
                  Строка {err.row}: {err.message}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      <div className="filter-bar" data-tour="timesheets-filters">
        <label className={shared.filterLabel}>
          <span>С</span>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="filter-select"
          />
        </label>
        <label className={shared.filterLabel}>
          <span>По</span>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="filter-select"
          />
        </label>
      </div>

      <div className={shared.summaryRow} data-tour="timesheets-summary">
        {summaryError ? (
          <span className="text-danger">{userFacingMessageFromUnknown(summaryErrorValue)}</span>
        ) : summaryPending || !summary ? (
          <span className={shared.summaryCount}>Загрузка сводки…</span>
        ) : (
          <>
            <div className={shared.summaryItem}>
              <span className={shared.summaryLabel}>Итого:</span>
              <span className={shared.summaryValue}>{formatMinutes(summary.total_minutes)}</span>
            </div>
            <span className={shared.summaryCount}>{summary.entries_count} записей</span>
          </>
        )}
      </div>

      <div className={shared.tabs} data-tour="timesheets-tabs">
        <button
          type="button"
          className={`${shared.tab} ${tab === 'entries' ? shared.tabActive : ''}`}
          onClick={() => selectTab('entries')}
        >
          Записи
        </button>
        <button
          type="button"
          className={`${shared.tab} ${tab === 'report' ? shared.tabActive : ''}`}
          onClick={() => selectTab('report')}
        >
          Отчёт по периодам
        </button>
      </div>

      {tab === 'entries' ? (
        <div data-tour="timesheets-entries">
          {isPending ? (
            <p className="text-muted">Загрузка…</p>
          ) : isError ? (
            <p className="text-danger">{userFacingMessageFromUnknown(error)}</p>
          ) : entries.length === 0 ? (
            <p className="text-muted">Записей нет</p>
          ) : (
            <>
              {entriesTruncated ? (
                <p className="text-muted">
                  Показаны первые {entries.length} из {entriesTotal} записей. Сузьте период фильтрами.
                </p>
              ) : null}
              <div className={panels.entriesList}>
                {dayGroups.map((group) => (
                  <DayGroupSection
                    key={group.worked_on}
                    workedOn={group.worked_on}
                    totalMinutes={group.totalMinutes}
                  >
                    {group.entries.map((entry) => (
                      <EntryRow
                        key={entry.id}
                        entry={entry}
                        onDelete={() => setDeleteConfirmId(entry.id)}
                        onUpdated={invalidateAll}
                      />
                    ))}
                  </DayGroupSection>
                ))}
              </div>
            </>
          )}
        </div>
      ) : (
        <div data-tour="timesheets-report">
          <TimeEntriesReportPanel dateFrom={dateFrom} dateTo={dateTo} />
        </div>
      )}

      {deleteConfirmId ? (
        <ConfirmDialog
          open
          title="Удалить запись?"
          message="Запись будет удалена без возможности восстановления."
          confirmLabel="Да, удалить"
          cancelLabel="Отмена"
          destructive
          confirmSound="error"
          disabled={deleteMutation.isPending}
          onConfirm={() => deleteMutation.mutate(deleteConfirmId)}
          onCancel={() => setDeleteConfirmId(null)}
        />
      ) : null}
    </div>
  )
}
