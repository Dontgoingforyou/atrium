import { MONTHS_FULL } from './monthCalendarUtils'
import { formatDateRu, todayStr } from '../time/timeEntryUtils'

export type DateParts = {
  year: number
  /** 0–11 */
  monthIndex: number
  day: number
}

export type DayGridCell = {
  dateStr: string
  day: number
  outsideMonth: boolean
}

function pad2(n: number): string {
  return String(n).padStart(2, '0')
}

export function parseDateStr(iso: string): DateParts | null {
  if (!iso) return null
  const [y, m, d] = iso.split('-').map(Number)
  if (!y || !m || m < 1 || m > 12 || !d || d < 1 || d > 31) return null
  const check = new Date(y, m - 1, d)
  if (
    check.getFullYear() !== y ||
    check.getMonth() !== m - 1 ||
    check.getDate() !== d
  ) {
    return null
  }
  return { year: y, monthIndex: m - 1, day: d }
}

export function dateStrFromParts(year: number, monthIndex: number, day: number): string {
  return `${year}-${pad2(monthIndex + 1)}-${pad2(day)}`
}

export function formatDayCalendarLabel(dateStr: string): string {
  if (!dateStr) return ''
  return formatDateRu(dateStr)
}

export function formatMonthYearTitle(year: number, monthIndex: number): string {
  return `${MONTHS_FULL[monthIndex]} ${year}`
}

export function todayDateStr(): string {
  return todayStr()
}

/** Понедельник = 0 … воскресенье = 6 */
function weekdayMon0(date: Date): number {
  return (date.getDay() + 6) % 7
}

export function buildMonthDayGrid(viewYear: number, viewMonthIndex: number): DayGridCell[] {
  const first = new Date(viewYear, viewMonthIndex, 1)
  const leading = weekdayMon0(first)
  const cells: DayGridCell[] = []

  for (let i = 0; i < 42; i += 1) {
    const offset = i - leading
    const date = new Date(viewYear, viewMonthIndex, 1 + offset)
    const y = date.getFullYear()
    const m = date.getMonth()
    const day = date.getDate()
    cells.push({
      dateStr: dateStrFromParts(y, m, day),
      day,
      outsideMonth: m !== viewMonthIndex || y !== viewYear,
    })
  }

  return cells
}

export function isDateDisabled(
  dateStr: string,
  minDate?: string,
  maxDate?: string,
): boolean {
  if (minDate && dateStr < minDate) return true
  if (maxDate && dateStr > maxDate) return true
  return false
}

export function dateStrToView(dateStr: string, fallback = new Date()): DateParts {
  return parseDateStr(dateStr) ?? {
    year: fallback.getFullYear(),
    monthIndex: fallback.getMonth(),
    day: fallback.getDate(),
  }
}
