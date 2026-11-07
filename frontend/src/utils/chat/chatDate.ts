import { parseApiDateTime } from '../time/parseApiDateTime'

const pad = (n: number) => n.toString().padStart(2, '0')

function calendarKey(d: Date): string {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

/** «Сегодня» / «Вчера» / локализованная дата. */
export function dayDividerLabelForDate(iso: string): 'Сегодня' | 'Вчера' | string {
  const d = parseApiDateTime(iso)
  if (!d) return '—'
  const today = new Date()
  if (calendarKey(d) === calendarKey(today)) {
    return 'Сегодня'
  }
  const y = new Date(today)
  y.setDate(y.getDate() - 1)
  if (calendarKey(d) === calendarKey(y)) {
    return 'Вчера'
  }
  const yNow = today.getFullYear()
  if (d.getFullYear() === yNow) {
    return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' })
  }
  return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })
}

export function timeOnly(iso: string): string {
  const d = parseApiDateTime(iso)
  if (!d) return '—'
  return d.toLocaleTimeString('ru-RU', {
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function insightAtLabel(iso: string): string {
  const day = dayDividerLabelForDate(iso)
  const t = timeOnly(iso)
  if (day === 'Сегодня') return `сегодня в ${t}`
  if (day === 'Вчера') return `вчера в ${t}`
  return `${day}, ${t}`
}

/** Сравнение календарных дней для разделителей ленты. */
export function sameCalendarDay(isoA: string, isoB: string): boolean {
  const a = parseApiDateTime(isoA)
  const b = parseApiDateTime(isoB)
  if (!a || !b) return false
  return calendarKey(a) === calendarKey(b)
}
