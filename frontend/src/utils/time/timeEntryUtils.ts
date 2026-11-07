import type { PortalTimeEntry, TimeEntryCreate } from '../../types/timeEntry'

const RU_MONTHS_GENITIVE = [
  'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
  'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря',
]

/** Максимум минут на одну запись (сутки). */
export const MAX_ENTRY_MINUTES_PER_DAY = 1440

/** Целевая длительность рабочего дня (8ч) — подсветка дней с отклонением. */
export const TARGET_DAY_MINUTES = 480

export function formatMinutes(m: number): string {
  const h = Math.floor(m / 60)
  const min = m % 60
  if (h === 0) return `${min} мин`
  if (min === 0) return `${h} ч`
  return `${h} ч ${min} мин`
}

export function todayStr(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

/**
 * Разбор поля «часы» (дробные) в минуты.
 * @returns минуты или null, если значение невалидно / вне (0, MAX_ENTRY_MINUTES_PER_DAY]
 */
export function parseHoursToMinutes(hoursRaw: string): number | null {
  const h = parseFloat(hoursRaw || '0')
  const totalMinutes = Math.round(h * 60)
  if (totalMinutes <= 0 || totalMinutes > MAX_ENTRY_MINUTES_PER_DAY) return null
  return totalMinutes
}

/** Текущий месяц в формате "YYYY-MM" (по локальному времени) */
export function currentMonthStr(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

/** Текущий месяц в формате "YYYY-MM" по UTC (как на бэкенде для лимита «не будущее»). */
export function currentMonthStrUtc(): string {
  const d = new Date()
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}`
}

/** Стартовый месяц для менеджерского экрана: локальный текущий, но не новее UTC-текущего. */
export function managerDefaultMonthStr(): string {
  const local = currentMonthStr()
  const maxUtc = currentMonthStrUtc()
  return local > maxUtc ? maxUtc : local
}

/** "YYYY-MM" → { from: "YYYY-MM-01", to: "YYYY-MM-DD" (последний день) } */
export function monthToDateRange(month: string): { from: string; to: string } {
  const [year, m] = month.split('-').map(Number)
  const lastDay = new Date(year, m, 0).getDate()
  return {
    from: `${month}-01`,
    to: `${month}-${String(lastDay).padStart(2, '0')}`,
  }
}

/** "YYYY-MM-DD" → "12 мая 2026" */
export function formatDateRu(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00')
  return `${d.getDate()} ${RU_MONTHS_GENITIVE[d.getMonth()]} ${d.getFullYear()}`
}

export type DayEntriesGroup = {
  worked_on: string
  totalMinutes: number
  entries: PortalTimeEntry[]
}

export function groupEntriesByDay(entries: PortalTimeEntry[]): DayEntriesGroup[] {
  const order: string[] = []
  const byDay = new Map<string, PortalTimeEntry[]>()
  for (const entry of entries) {
    const existing = byDay.get(entry.worked_on)
    if (existing) {
      existing.push(entry)
    } else {
      byDay.set(entry.worked_on, [entry])
      order.push(entry.worked_on)
    }
  }
  return order.map((worked_on) => {
    const dayEntries = byDay.get(worked_on) as PortalTimeEntry[]
    return {
      worked_on,
      totalMinutes: dayEntries.reduce((sum, e) => sum + e.minutes, 0),
      entries: dayEntries,
    }
  })
}

export const WEEKDAY_LABELS_SHORT = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
export const DEFAULT_BULK_WEEKDAYS = [0, 1, 2, 3, 4]

function toDateStr(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export function generateWeekdayDates(dateFrom: string, dateTo: string, weekdays: number[]): string[] {
  if (!dateFrom || !dateTo) return []
  const start = new Date(dateFrom + 'T00:00:00')
  const end = new Date(dateTo + 'T00:00:00')
  if (start > end) return []
  const allowed = new Set(weekdays)
  const dates: string[] = []
  const cur = new Date(start)
  while (cur <= end) {
    const weekday = (cur.getDay() + 6) % 7 // JS: 0=Вс..6=Сб → 0=Пн..6=Вс
    if (allowed.has(weekday)) {
      dates.push(toDateStr(cur))
    }
    cur.setDate(cur.getDate() + 1)
  }
  return dates
}

export function buildDuplicateTimeEntryCreate(
  entry: PortalTimeEntry,
  overrides: { worked_on: string; minutes: number; task_name?: string; note?: string },
): TimeEntryCreate {
  return {
    worked_on: overrides.worked_on,
    minutes: overrides.minutes,
    task_id: entry.task_id,
    task_name:
      overrides.task_name !== undefined
        ? overrides.task_name.trim() || null
        : entry.task_name,
    note:
      overrides.note !== undefined ? overrides.note.trim() || null : entry.note,
  }
}
