import { useState } from 'react'
import { GroupingSelect } from '../../components/analytics/GroupingSelect'
import { MonthYearPeriodPicker } from '../../components/analytics/MonthYearPeriodPicker'
import { DateRangePicker } from '../../components/common/DateRangePicker'
import { TimeEntriesReportPanel } from '../timesheets/TimeEntriesReportPanel'
import monthPickerStyles from '@/styles/modules/common/MonthCalendarPicker.module.css'
import styles from '@/styles/modules/analytics/AnalyticsReportsPage.module.css'

export function AnalyticsReportsPage() {
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [groupBy, setGroupBy] = useState<'week' | 'month'>('week')

  function handlePeriodChange(from: string, to: string) {
    setDateFrom(from)
    setDateTo(to)
  }

  const pickerClassName = monthPickerStyles.fixedWidth

  return (
    <div>
      <p className={`text-muted ${styles.intro}`}>
        Сводка трудозатрат по неделям и месяцам. Укажите период или оставьте пустым для всех доступных записей.
      </p>
      <div className={styles.filters} data-tour="analytics-reports-filters">
        <div className={styles.filterToolbar}>
          <MonthYearPeriodPicker
            dateFrom={dateFrom}
            dateTo={dateTo}
            onChange={handlePeriodChange}
            pickerClassName={pickerClassName}
            resetButtonClassName={styles.resetBtn}
            rowClassName={styles.filterRow}
          />
          <DateRangePicker
            dateFrom={dateFrom}
            dateTo={dateTo}
            onChange={handlePeriodChange}
            rowClassName={styles.filterRow}
            placeholder="дд.мм.гггг"
          />
          <GroupingSelect value={groupBy} onChange={setGroupBy} />
        </div>
      </div>
      <div data-tour="analytics-reports-table">
        <TimeEntriesReportPanel
          dateFrom={dateFrom}
          dateTo={dateTo}
          groupBy={groupBy}
          hideGroupingFilter
          reportContentClassName={styles.reportContent}
        />
      </div>
    </div>
  )
}
