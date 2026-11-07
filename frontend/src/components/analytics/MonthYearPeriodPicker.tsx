import { useMemo } from 'react'
import { MonthCalendarPicker } from '../common/MonthCalendarPicker'
import {
  monthStrFromValue,
  monthStrToCalendarValue,
} from '../../utils/calendar/monthCalendarUtils'
import { monthToDateRange } from '@/utils/time/timeEntryUtils'
import { IconReset } from '../icons/portalIcons'
import ownStyles from '@/styles/modules/analytics/MonthYearPeriodPicker.module.css'

type Props = {
  dateFrom: string
  dateTo: string
  onChange: (from: string, to: string) => void
  pickerClassName?: string
  resetButtonClassName?: string
  rowClassName?: string
}

function monthFromDateFrom(dateFrom: string): string {
  if (!dateFrom) return ''
  const [y, m] = dateFrom.split('-')
  if (y && m) return `${y}-${m}`
  return ''
}

export function MonthYearPeriodPicker({
  dateFrom,
  dateTo,
  onChange,
  pickerClassName,
  resetButtonClassName,
  rowClassName,
}: Props) {
  const monthStr = monthFromDateFrom(dateFrom)
  const value = useMemo(() => {
    const now = new Date()
    const fallback = monthStrFromValue({ year: now.getFullYear(), monthIndex: now.getMonth() })
    return monthStrToCalendarValue(monthStr || fallback, now)
  }, [monthStr])

  function apply(next: { year: number; monthIndex: number }) {
    const { from, to } = monthToDateRange(monthStrFromValue(next))
    onChange(from, to)
  }

  return (
    <div className={rowClassName ?? ownStyles.row}>
      <MonthCalendarPicker
        value={value}
        label=""
        onChange={apply}
        className={pickerClassName}
      />
      {(dateFrom || dateTo) && (
        <button
          type="button"
          className={['btn-secondary', resetButtonClassName].filter(Boolean).join(' ')}
          onClick={() => onChange('', '')}
        >
          <IconReset />
          Сбросить период
        </button>
      )}
    </div>
  )
}
