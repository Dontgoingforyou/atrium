/**
 * Парсинг дат из API для WebKit (Safari): нормализует ISO-подобные строки.
 * Safari не принимает "2024-01-15 12:00:00" без T и часть форматов без timezone.
 */
export function parseApiDateTime(iso: string | null | undefined): Date | null {
  if (iso == null || iso === '' || iso === 'undefined' || iso === 'null') {
    return null
  }
  let s = String(iso).trim()
  if (!s) return null

  // "2024-01-15 12:00:00" → "2024-01-15T12:00:00"
  if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}/.test(s) && !s.includes('T')) {
    s = s.replace(' ', 'T')
  }
  // Дата+время без Z/offset — трактуем как UTC (как типичный JSON от Pydantic)
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(s) && !/[zZ]|[+-]\d{2}:?\d{2}$/.test(s)) {
    s = `${s}Z`
  }

  const d = new Date(s)
  if (Number.isNaN(d.getTime())) return null
  return d
}
