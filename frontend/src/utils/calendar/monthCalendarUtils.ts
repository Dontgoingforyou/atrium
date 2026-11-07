export type MonthCalendarValue = {
  year: number
  /** 0–11 */
  monthIndex: number
}

export function parseMonthStr(monthStr: string): MonthCalendarValue | null {
  const [y, m] = monthStr.split('-').map(Number)
  if (!y || !m || m < 1 || m > 12) return null
  return { year: y, monthIndex: m - 1 }
}

export function monthStrFromValue(v: MonthCalendarValue): string {
  return `${v.year}-${String(v.monthIndex + 1).padStart(2, '0')}`
}

export const MONTHS_FULL = [
  'Январь',
  'Февраль',
  'Март',
  'Апрель',
  'Май',
  'Июнь',
  'Июль',
  'Август',
  'Сентябрь',
  'Октябрь',
  'Ноябрь',
  'Декабрь',
] as const

export const MONTHS_SHORT = [
  'Янв',
  'Фев',
  'Мар',
  'Апр',
  'Май',
  'Июн',
  'Июл',
  'Авг',
  'Сен',
  'Окт',
  'Ноя',
  'Дек',
] as const

export function formatMonthCalendarLabel(v: MonthCalendarValue): string {
  return `${MONTHS_FULL[v.monthIndex]} ${v.year}`
}

export function monthStrToCalendarValue(monthStr: string, fallback = new Date()): MonthCalendarValue {
  return parseMonthStr(monthStr) ?? {
    year: fallback.getFullYear(),
    monthIndex: fallback.getMonth(),
  }
}

export function monthStrFromCalendarValue(v: MonthCalendarValue): string {
  return monthStrFromValue(v)
}

export function isMonthDisabled(
  year: number,
  monthIndex: number,
  minMonth?: string,
  maxMonth?: string,
): boolean {
  const cur = monthStrFromValue({ year, monthIndex })
  if (maxMonth && cur > maxMonth) return true
  if (minMonth && cur < minMonth) return true
  return false
}

/** Размер сетки выбора года (как у месяцев — 12 ячеек). */
export const YEAR_PAGE_SIZE = 12

/** Начало страницы лет, содержащей `year` (кратное YEAR_PAGE_SIZE). */
export function yearPageStart(year: number): number {
  return Math.floor(year / YEAR_PAGE_SIZE) * YEAR_PAGE_SIZE
}

/** 12 лет страницы, начиная с `pageStart`. */
export function yearsInPage(pageStart: number): number[] {
  return Array.from({ length: YEAR_PAGE_SIZE }, (_, i) => pageStart + i)
}
