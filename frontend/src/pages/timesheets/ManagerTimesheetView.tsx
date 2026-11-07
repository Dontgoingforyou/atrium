import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listSpecialistsSummary } from '../../api/timeEntries/timeEntriesApi'
import { timeEntriesSpecialistsQueryKey } from '../../api/queryKeys'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { getUserDisplayLabel } from '../../utils/userLabel'
import { MonthCalendarPicker } from '../../components/common/MonthCalendarPicker'
import {
  monthStrFromCalendarValue,
  monthStrToCalendarValue,
} from '../../utils/calendar/monthCalendarUtils'
import {
  currentMonthStrUtc,
  managerDefaultMonthStr,
} from '@/utils/time/timeEntryUtils'
import { SpecialistCard } from './SpecialistCard'
import styles from '@/styles/modules/timesheets/TimesheetsPagePanels.module.css'

const SPECIALISTS_LIST_LIMIT = 200

export function ManagerTimesheetView() {
  const [month, setMonth] = useState(managerDefaultMonthStr)
  const [expandedSub, setExpandedSub] = useState<string | null>(null)
  const [sortAsc, setSortAsc] = useState(true)

  const { data, isPending, isError, error } = useQuery({
    queryKey: timeEntriesSpecialistsQueryKey({ month }),
    queryFn: () => listSpecialistsSummary({ month, limit: SPECIALISTS_LIST_LIMIT }),
  })

  const specialists = data?.items ?? []
  const total = data?.total ?? 0
  const truncated = specialists.length < total
  const sorted = [...specialists].sort((a, b) => {
    const nameA = getUserDisplayLabel({
      sub: a.user_sub,
      display_name: a.full_name,
      email: a.email,
    })
    const nameB = getUserDisplayLabel({
      sub: b.user_sub,
      display_name: b.full_name,
      email: b.email,
    })
    return sortAsc ? nameA.localeCompare(nameB, 'ru') : nameB.localeCompare(nameA, 'ru')
  })

  function toggleExpand(sub: string) {
    setExpandedSub((prev) => (prev === sub ? null : sub))
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Таймшиты специалистов</h1>
      </div>

      <div data-tour="analytics-timesheets-month">
        <MonthCalendarPicker
          value={monthStrToCalendarValue(month)}
          label=""
          maxMonth={currentMonthStrUtc()}
          className={styles.monthPicker}
          onChange={(next) => {
            setMonth(monthStrFromCalendarValue(next))
            setExpandedSub(null)
          }}
        />
      </div>

      <div className={styles.managerToolbar}>
        <span className={styles.specialistsCount}>
          {isPending
            ? 'Загрузка…'
            : truncated
              ? `${specialists.length} из ${total} специалистов`
              : `${total} специалистов`}
        </span>
        <button
          type="button"
          className={styles.sortBtn}
          onClick={() => setSortAsc((v) => !v)}
          title="Сортировка по имени"
        >
          По имени {sortAsc ? '↑' : '↓'}
        </button>
      </div>

      {truncated && !isPending && !isError ? (
        <p className="text-muted">
          Список усечён до {SPECIALISTS_LIST_LIMIT} специалистов. Показаны первые по ответу API.
        </p>
      ) : null}

      {isError ? (
        <p className="text-danger">{userFacingMessageFromUnknown(error)}</p>
      ) : isPending ? null : sorted.length === 0 ? (
        <p className="text-muted" data-tour="analytics-timesheets-list">
          За этот месяц записей нет
        </p>
      ) : (
        <div className={styles.specialistsList} data-tour="analytics-timesheets-list">
          {sorted.map((s) => (
            <SpecialistCard
              key={s.user_sub}
              specialist={s}
              month={month}
              expanded={expandedSub === s.user_sub}
              onToggle={() => toggleExpand(s.user_sub)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
