export function formatLastSeenBrief(iso: string): string {
  const then = new Date(iso).getTime()
  if (Number.isNaN(then)) return 'Не в сети'
  const seconds = Math.round((Date.now() - then) / 1000)
  if (seconds < 15) return 'Был(а) только что'

  const rtf = new Intl.RelativeTimeFormat('ru', { numeric: 'auto' })

  if (seconds < 60) {
    return `Был(а) ${rtf.format(-seconds, 'second')}`
  }
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) {
    return `Был(а) ${rtf.format(-minutes, 'minute')}`
  }
  const hours = Math.floor(minutes / 60)
  if (hours < 24) {
    return `Был(а) ${rtf.format(-hours, 'hour')}`
  }
  const days = Math.floor(hours / 24)
  if (days < 7) {
    return `Был(а) ${rtf.format(-days, 'day')}`
  }
  const weeks = Math.floor(days / 7)
  if (weeks < 5) {
    return `Был(а) ${rtf.format(-weeks, 'week')}`
  }
  const months = Math.floor(days / 30)
  if (months < 12) {
    return `Был(а) ${rtf.format(-months, 'month')}`
  }
  const years = Math.floor(days / 365)
  return `Был(а) ${rtf.format(-years, 'year')}`
}
