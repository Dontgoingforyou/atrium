/** Пресеты RRULE для формы события. */
export type RrulePreset = 'none' | 'daily' | 'weekdays' | 'weekly' | 'monthly'

export function rruleFromPreset(preset: RrulePreset): string | null {
  switch (preset) {
    case 'daily':
      return 'FREQ=DAILY'
    case 'weekdays':
      return 'FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR'
    case 'weekly':
      return 'FREQ=WEEKLY'
    case 'monthly':
      return 'FREQ=MONTHLY'
    default:
      return null
  }
}

export function presetFromRrule(rrule: string | null | undefined): RrulePreset {
  if (!rrule) return 'none'
  const u = rrule.toUpperCase()
  if (u.includes('BYDAY=MO,TU,WE,TH,FR')) return 'weekdays'
  if (u.startsWith('FREQ=DAILY')) return 'daily'
  if (u.startsWith('FREQ=WEEKLY')) return 'weekly'
  if (u.startsWith('FREQ=MONTHLY')) return 'monthly'
  return 'none'
}

export function startOfMonth(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), 1)
}

export function endOfMonth(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth() + 1, 1)
}

export function startOfWeek(d: Date): Date {
  const x = new Date(d)
  const day = (x.getDay() + 6) % 7 // Monday=0
  x.setDate(x.getDate() - day)
  x.setHours(0, 0, 0, 0)
  return x
}

export function addDays(d: Date, n: number): Date {
  const x = new Date(d)
  x.setDate(x.getDate() + n)
  return x
}

export function toIso(d: Date): string {
  return d.toISOString()
}

export function formatDayLabel(d: Date): string {
  return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })
}

export function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
}
