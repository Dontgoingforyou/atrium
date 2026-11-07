import { useMemo } from 'react'

import { DateRangePicker } from '../../../components/common/DateRangePicker'
import { SearchableMultiPicker } from '../../../components/common/SearchableMultiPicker'
import { AddableFilterBar, type AddableFilterField } from '../../../components/common/AddableFilterBar'
import { MonthYearPeriodPicker } from '../../../components/analytics/MonthYearPeriodPicker'
import {
  BENCH_FILTER_PERIOD_LABEL,
  BENCH_FILTER_SPECIALIZATION_LABEL,
  benchSpecializationPickerOptions,
  formatBenchPeriodLabels,
} from './benchFilterOptions'
import monthPickerStyles from '@/styles/modules/common/MonthCalendarPicker.module.css'
import styles from '@/styles/modules/analytics/AnalyticsBenchPage.module.css'
import taskShell from '@/styles/modules/tasks/TasksPageShell.module.css'

type Props = {
  specializationsSelected: string[]
  onSpecializationsChange: (value: string[]) => void
  specializations: string[]
  dateFrom: string
  dateTo: string
  onPeriodChange: (from: string, to: string) => void
  hasActiveFilters: boolean
  onReset: () => void
}

export function BenchFilters({
  specializationsSelected,
  onSpecializationsChange,
  specializations,
  dateFrom,
  dateTo,
  onPeriodChange,
  hasActiveFilters,
  onReset,
}: Props) {
  const fields: AddableFilterField[] = useMemo(
    () => [
      {
        id: 'specialization',
        label: BENCH_FILTER_SPECIALIZATION_LABEL,
        hasValues: specializationsSelected.length > 0,
        selectedLabels: specializationsSelected,
        defaultActive: true,
        onClear: () => onSpecializationsChange([]),
        renderPicker: () => (
          <SearchableMultiPicker
            value={specializationsSelected}
            onChange={onSpecializationsChange}
            options={benchSpecializationPickerOptions(specializations)}
            placeholder="Все — начните вводить специализацию…"
            chipsAriaLabel="Выбранные специализации"
          />
        ),
      },
      {
        id: 'period',
        label: BENCH_FILTER_PERIOD_LABEL,
        hasValues: Boolean(dateFrom || dateTo),
        selectedLabels: formatBenchPeriodLabels(dateFrom, dateTo),
        defaultActive: true,
        onClear: () => onPeriodChange('', ''),
        renderPicker: () => (
          <div className={styles.periodPicker}>
            <MonthYearPeriodPicker
              dateFrom={dateFrom}
              dateTo={dateTo}
              onChange={onPeriodChange}
              pickerClassName={monthPickerStyles.fixedWidth}
              resetButtonClassName={styles.resetBtn}
            />
            <DateRangePicker
              dateFrom={dateFrom}
              dateTo={dateTo}
              onChange={onPeriodChange}
              placeholder="дд.мм.гггг"
            />
          </div>
        ),
      },
    ],
    [
      specializationsSelected,
      onSpecializationsChange,
      specializations,
      dateFrom,
      dateTo,
      onPeriodChange,
    ],
  )

  return (
    <div className={`${taskShell.controls} ${styles.filters}`}>
      <div className={taskShell.controlsMain}>
        <AddableFilterBar
          fields={fields}
          hasActiveFilters={hasActiveFilters}
          resetFilters={onReset}
        />
      </div>
    </div>
  )
}
