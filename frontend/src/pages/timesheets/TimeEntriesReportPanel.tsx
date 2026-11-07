import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getTimeEntriesReport } from '../../api/timeEntries/timeEntriesApi'
import { timeEntriesReportQueryKey } from '../../api/queryKeys'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { formatMinutes } from '@/utils/time/timeEntryUtils'
import styles from '@/styles/modules/timesheets/TimesheetsPageShared.module.css'

/** Отчёт по периодам (недели/месяцы); используется на странице «Аналитика → Отчёты». */
export function TimeEntriesReportPanel({
  dateFrom,
  dateTo,
  groupBy: groupByProp,
  hideGroupingFilter,
  groupingClassName,
  groupingLabelClassName,
  groupingSelectClassName,
  filterRowClassName,
  panelClassName,
  reportContentClassName,
}: {
  dateFrom: string
  dateTo: string
  groupBy?: 'week' | 'month'
  hideGroupingFilter?: boolean
  groupingClassName?: string
  groupingLabelClassName?: string
  groupingSelectClassName?: string
  filterRowClassName?: string
  panelClassName?: string
  reportContentClassName?: string
}) {
  const [internalGroupBy, setInternalGroupBy] = useState<'week' | 'month'>('week')
  const groupBy = groupByProp ?? internalGroupBy
  const showGroupingFilter = !hideGroupingFilter && groupByProp === undefined

  const { data, isPending, isError, error } = useQuery({
    queryKey: timeEntriesReportQueryKey({ groupBy, dateFrom, dateTo }),
    queryFn: () =>
      getTimeEntriesReport({
        group_by: groupBy,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      }),
  })

  const total = data?.reduce((acc, b) => acc + b.total_minutes, 0) ?? 0
  const totalCount = data?.reduce((acc, b) => acc + b.entries_count, 0) ?? 0

  const contentClass = reportContentClassName ?? ''
  const filterRowCls = filterRowClassName
    ? filterRowClassName
    : `filter-bar ${styles.reportFilterRow}`

  return (
    <div className={panelClassName}>
      {showGroupingFilter ? (
        <div className={filterRowCls}>
          {groupingClassName ? (
            <label className={groupingClassName}>
              <span className={groupingLabelClassName}>Группировка:</span>
              <select
                value={groupBy}
                onChange={(e) => setInternalGroupBy(e.target.value as 'week' | 'month')}
                className={groupingSelectClassName}
              >
                <option value="week">По неделям</option>
                <option value="month">По месяцам</option>
              </select>
            </label>
          ) : (
            <label className={styles.filterLabel}>
              <span>Группировка:</span>
              <select
                value={groupBy}
                onChange={(e) => setInternalGroupBy(e.target.value as 'week' | 'month')}
                className="filter-select"
              >
                <option value="week">По неделям</option>
                <option value="month">По месяцам</option>
              </select>
            </label>
          )}
        </div>
      ) : null}

      {isPending ? (
        <p className={`text-muted ${contentClass}`.trim()}>Загрузка…</p>
      ) : isError ? (
        <p className={`text-danger ${contentClass}`.trim()}>{userFacingMessageFromUnknown(error)}</p>
      ) : !data || data.length === 0 ? (
        <p className={`text-muted ${contentClass}`.trim()}>Данных нет</p>
      ) : (
        <div className={`${styles.reportScroll} ${contentClass}`.trim()}>
          <table className={styles.reportTable} data-tour="timesheets-report-table">
            <thead>
              <tr>
                <th>Период</th>
                <th>Дата начала</th>
                <th>Дата конца</th>
                <th>Записей</th>
                <th>Итого</th>
              </tr>
            </thead>
            <tbody>
              {data.map((bucket) => (
                <tr key={bucket.period_label}>
                  <td>{bucket.period_label}</td>
                  <td>{new Date(bucket.date_start).toLocaleDateString('ru-RU')}</td>
                  <td>{new Date(bucket.date_end).toLocaleDateString('ru-RU')}</td>
                  <td className={styles.reportMetric}>{bucket.entries_count}</td>
                  <td className={styles.reportMetric}>{formatMinutes(bucket.total_minutes)}</td>
                </tr>
              ))}
              {data.length > 1 ? (
                <tr className={styles.reportTotalRow}>
                  <td colSpan={3}>Итого</td>
                  <td className={styles.reportMetric}>{totalCount}</td>
                  <td className={styles.reportMetric}>{formatMinutes(total)}</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
