/**
 * Дата (без времени) в таймзоне МСК, формат `dd.mm.yyyy`.
 *
 * UTC-даты из API показываем пользователю в Europe/Moscow — единая конвенция
 * портала (см. историю коммитов про «время уведомлений в МСК»). На UI-границе
 * перевод из UTC в локальную зону допустим (general.mdc).
 */
export function formatMskDate(iso: string): string {
  const dt = new Date(iso)
  if (Number.isNaN(dt.getTime())) {
    return iso
  }
  try {
    return new Intl.DateTimeFormat('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      timeZone: 'Europe/Moscow',
    }).format(dt)
  } catch {
    return new Intl.DateTimeFormat('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    }).format(dt)
  }
}
