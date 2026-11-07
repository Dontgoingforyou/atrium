/** Локальный datetime-формат для `<input type="datetime-local">`-подобных строк: `YYYY-MM-DDTHH:mm`. */

export function joinLocal(date: string, time: string): string {
  if (!date) return ''
  return `${date}T${time || '00:00'}`
}

export function splitLocal(dtLocal: string): { date: string; time: string } {
  if (!dtLocal) return { date: '', time: '10:00' }
  const [date, timePart] = dtLocal.split('T')
  return { date: date ?? '', time: (timePart ?? '10:00').slice(0, 5) }
}

/** `Date` → локальная строка `YYYY-MM-DDTHH:mm` (без временной зоны). */
export function toLocalInput(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/** ISO-строка → локальная строка `YYYY-MM-DDTHH:mm` (без временной зоны). */
export function toLocalFromIso(iso: string): string {
  return toLocalInput(new Date(iso))
}

/** Локальные дата и время: начало плюс один час, дата сдвигается через полночь. */
export function plusOneHourLocal(date: string, time: string): { date: string; time: string } {
  const [year, month, day] = date.split('-').map(Number)
  const [hours, minutes] = time.split(':').map(Number)
  const start = new Date(year ?? 0, (month ?? 1) - 1, day ?? 1, hours ?? 0, minutes ?? 0, 0, 0)
  start.setHours(start.getHours() + 1)
  return splitLocal(toLocalInput(start))
}
