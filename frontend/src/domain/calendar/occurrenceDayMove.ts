import type { PortalCalendarOccurrence } from '../../types/calendar'

type DayMoveSource = Pick<
  PortalCalendarOccurrence,
  | 'event_id'
  | 'calendar_id'
  | 'original_start'
  | 'starts_at'
  | 'ends_at'
  | 'rrule'
  | 'title'
  | 'description'
  | 'location'
>

export type OccurrenceDayMove = {
  event_id: string
  calendar_id: string
  original_start: string
  starts_at: string
  ends_at: string | null
} & (
  | { kind: 'patch' }
  | {
      kind: 'override'
      title: string
      description: string | null
      location: string | null
    }
)

const DAY_PREFIX = 'cal-day:'

function localDaySerial(day: Date): number {
  return Date.UTC(day.getFullYear(), day.getMonth(), day.getDate()) / 86_400_000
}

function addLocalDays(day: Date, delta: number): Date {
  const next = new Date(day)
  next.setDate(next.getDate() + delta)
  return next
}

export function planOccurrenceDayMove(occurrence: DayMoveSource, targetDay: Date): OccurrenceDayMove | null {
  const start = new Date(occurrence.starts_at)
  if (Number.isNaN(start.getTime()) || Number.isNaN(targetDay.getTime())) return null
  const dayDelta = localDaySerial(targetDay) - localDaySerial(start)
  if (dayDelta === 0) return null
  const startsAt = addLocalDays(start, dayDelta).toISOString()
  let endsAt: string | null = null
  if (occurrence.ends_at) {
    const end = new Date(occurrence.ends_at)
    if (Number.isNaN(end.getTime())) return null
    endsAt = addLocalDays(end, dayDelta).toISOString()
  }
  const shared = {
    event_id: occurrence.event_id,
    calendar_id: occurrence.calendar_id,
    original_start: occurrence.original_start,
    starts_at: startsAt,
    ends_at: endsAt,
  }
  if (occurrence.rrule) {
    return {
      kind: 'override',
      ...shared,
      title: occurrence.title,
      description: occurrence.description,
      location: occurrence.location,
    }
  }
  return { kind: 'patch', ...shared }
}

export function applyOccurrenceDayMove(
  items: PortalCalendarOccurrence[],
  move: OccurrenceDayMove,
): PortalCalendarOccurrence[] {
  return items.map((occ) =>
    occ.event_id === move.event_id && occ.original_start === move.original_start
      ? { ...occ, starts_at: move.starts_at, ends_at: move.ends_at }
      : occ,
  )
}

export function calendarDayDropId(day: Date): string {
  const month = String(day.getMonth() + 1).padStart(2, '0')
  const date = String(day.getDate()).padStart(2, '0')
  return `${DAY_PREFIX}${day.getFullYear()}-${month}-${date}`
}

export function parseCalendarDayDropId(id: string): Date | null {
  if (!id.startsWith(DAY_PREFIX)) return null
  const [yearRaw, monthRaw, dateRaw] = id.slice(DAY_PREFIX.length).split('-')
  const year = Number(yearRaw)
  const month = Number(monthRaw)
  const date = Number(dateRaw)
  if (!Number.isInteger(year) || !Number.isInteger(month) || !Number.isInteger(date)) return null
  const day = new Date(year, month - 1, date)
  if (day.getFullYear() !== year || day.getMonth() !== month - 1 || day.getDate() !== date) return null
  return day
}

export function calendarOccurrenceDragId(eventId: string, originalStart: string): string {
  return `cal-occ:${eventId}:${originalStart}`
}
