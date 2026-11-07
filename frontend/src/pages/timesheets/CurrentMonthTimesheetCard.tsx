import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getTimeEntrySummary } from '../../api/timeEntries/timeEntriesApi'
import { timeEntriesSummaryQueryKey } from '../../api/queryKeys'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { formatMinutes } from '@/utils/time/timeEntryUtils'
import styles from '@/styles/modules/timesheets/CurrentMonthTimesheetCard.module.css'

function currentMonthStart(): string {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-01`
}

export function CurrentMonthTimesheetCard() {
  const monthStart = useMemo(() => currentMonthStart(), [])
  const { data, isError, error } = useQuery({
    queryKey: timeEntriesSummaryQueryKey({ dateFrom: monthStart }),
    queryFn: () => getTimeEntrySummary({ date_from: monthStart }),
  })

  return (
    <section className={styles.card} data-tour="analytics-summary-timesheets">
      <h2 className={styles.cardTitle}>Таймшиты (текущий месяц)</h2>
      {isError ? (
        <p className="text-danger">{userFacingMessageFromUnknown(error)}</p>
      ) : data ? (
        <div className={styles.kpiRow}>
          <div className={styles.kpiItem}>
            <span className={styles.kpiValue}>{formatMinutes(data.total_minutes)}</span>
            <span className={styles.kpiLabel}>Итого</span>
          </div>
          <div className={styles.kpiItem}>
            <span className={styles.kpiValue}>{data.entries_count}</span>
            <span className={styles.kpiLabel}>Записей</span>
          </div>
        </div>
      ) : (
        <p className="text-muted">Загрузка…</p>
      )}
    </section>
  )
}
