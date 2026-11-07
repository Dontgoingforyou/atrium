import type { ReactNode } from 'react'
import { formatDateRu, formatMinutes, TARGET_DAY_MINUTES } from '@/utils/time/timeEntryUtils'
import panels from '@/styles/modules/timesheets/TimesheetsPagePanels.module.css'

export function DayGroupSection({
  workedOn,
  totalMinutes,
  children,
}: {
  workedOn: string
  totalMinutes: number
  children: ReactNode
}) {
  const isOffTarget = totalMinutes !== TARGET_DAY_MINUTES
  return (
    <div className={panels.dayGroup}>
      <div className={panels.dayGroupHeader}>
        <span className={panels.dayGroupDate}>{formatDateRu(workedOn)}</span>
        <span className={`${panels.dayGroupTotal} ${isOffTarget ? panels.dayGroupTotalWarn : ''}`}>
          {formatMinutes(totalMinutes)}
        </span>
      </div>
      <div className={panels.dayGroupEntries}>{children}</div>
    </div>
  )
}
