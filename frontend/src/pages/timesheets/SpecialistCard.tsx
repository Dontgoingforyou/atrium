import { useId, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { exportTimeEntries, listTimeEntries } from '../../api/timeEntries/timeEntriesApi'
import { timeEntriesQueryKey } from '../../api/queryKeys'
import type { PortalSpecialistMonthlySummary } from '../../types/timeEntry'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { getUserDisplayLabel } from '../../utils/userLabel'
import { formatMinutes, groupEntriesByDay } from '@/utils/time/timeEntryUtils'
import { DayGroupSection } from './DayGroupSection'
import styles from '@/styles/modules/timesheets/TimesheetsPagePanels.module.css'

/** Месячный список записей специалиста — API допускает до 500. */
const SPECIALIST_ENTRIES_LIMIT = 500

export function SpecialistCard({
  specialist,
  month,
  expanded,
  onToggle,
}: {
  specialist: PortalSpecialistMonthlySummary
  month: string
  expanded: boolean
  onToggle: () => void
}) {
  const panelId = useId()
  const displayName = getUserDisplayLabel({
    sub: specialist.user_sub,
    display_name: specialist.full_name,
    email: specialist.email,
  })
  const [exportErr, setExportErr] = useState<string | null>(null)
  const [exporting, setExporting] = useState(false)

  async function handleExport(format: 'csv' | 'xlsx' | 'pdf') {
    setExporting(true)
    setExportErr(null)
    try {
      await exportTimeEntries({ format, month, user_sub: specialist.user_sub })
    } catch (e) {
      setExportErr(userFacingMessageFromUnknown(e))
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className={`${styles.specialistCard} ${expanded ? styles.specialistCardExpanded : ''}`}>
      <button
        type="button"
        className={styles.specialistHeader}
        onClick={onToggle}
        aria-expanded={expanded}
        aria-controls={panelId}
      >
        <div className={styles.specialistInfo}>
          <span className={styles.specialistName}>{displayName}</span>
          {specialist.full_name && specialist.email ? (
            <span className={styles.specialistEmail}>{specialist.email}</span>
          ) : null}
        </div>
        <div className={styles.specialistStats}>
          <span className={styles.specialistHours}>{formatMinutes(specialist.total_minutes)}</span>
          <span className={styles.specialistEntriesCount}>{specialist.entries_count} зап.</span>
          <span className={styles.specialistChevron} aria-hidden>
            {expanded ? '▲' : '▼'}
          </span>
        </div>
      </button>

      <div className={styles.specialistExportRow}>
        <span className={styles.specialistExportLabel}>Выгрузить:</span>
        {(['csv', 'xlsx', 'pdf'] as const).map((fmt) => (
          <button
            key={fmt}
            type="button"
            className={styles.exportBtn}
            disabled={exporting}
            onClick={(e) => {
              e.stopPropagation()
              void handleExport(fmt)
            }}
            title={`Скачать ${fmt.toUpperCase()} за ${month}`}
          >
            {fmt.toUpperCase()}
          </button>
        ))}
        {exportErr && <span className={styles.exportError}>{exportErr}</span>}
      </div>

      {expanded ? (
        <div id={panelId}>
          <SpecialistEntriesPanel userSub={specialist.user_sub} month={month} />
        </div>
      ) : (
        <div id={panelId} hidden />
      )}
    </div>
  )
}

function SpecialistEntriesPanel({ userSub, month }: { userSub: string; month: string }) {
  const { data, isPending, isError, error } = useQuery({
    queryKey: timeEntriesQueryKey({ userSub, month }),
    queryFn: () =>
      listTimeEntries({ user_sub: userSub, month, limit: SPECIALIST_ENTRIES_LIMIT }),
  })

  const entries = data?.items ?? []
  const total = data?.total ?? 0
  const dayGroups = groupEntriesByDay(entries)
  const truncated = entries.length < total

  if (isPending) return <p className={styles.panelLoading}>Загрузка…</p>
  if (isError) return <p className="text-danger">{userFacingMessageFromUnknown(error)}</p>
  if (entries.length === 0) {
    return <p className={styles.panelEmpty}>Записей нет</p>
  }

  return (
    <div className={styles.specialistEntries}>
      {truncated ? (
        <p className="text-muted">
          Показаны первые {entries.length} из {total} записей. Сузьте период или выгрузите файл.
        </p>
      ) : null}
      {dayGroups.map((group) => (
        <DayGroupSection key={group.worked_on} workedOn={group.worked_on} totalMinutes={group.totalMinutes}>
          {group.entries.map((entry) => (
            <div key={entry.id} className={styles.managerEntryRow}>
              <div className={styles.managerEntryBody}>
                {entry.task_name ? (
                  <span className={styles.managerEntryTask}>{entry.task_name}</span>
                ) : null}
                {entry.note ? (
                  <span className={styles.managerEntryNote}>{entry.note}</span>
                ) : null}
              </div>
              <div className={styles.managerEntryHours}>{formatMinutes(entry.minutes)}</div>
            </div>
          ))}
        </DayGroupSection>
      ))}
    </div>
  )
}
