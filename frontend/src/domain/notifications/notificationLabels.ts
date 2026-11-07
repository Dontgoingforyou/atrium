import type { PortalNotification } from '../../types/notification'

export function notificationPrimaryLine(notif: PortalNotification): string {
  if (notif.type === 'task_mention' || notif.type === 'document_mention') {
    return `${notif.author_display_name ?? notif.author_sub} упомянул вас`
  }
  if (notif.type === 'task_assigned') {
    return `${notif.author_display_name ?? notif.author_sub} назначил(а) вам задачу`
  }
  if (notif.type === 'task_due_soon') {
    return 'Срок задачи через 2 дня'
  }
  if (notif.type === 'task_overdue') {
    return 'Задача просрочена'
  }
  if (notif.type === 'task_comment') {
    return `${notif.author_display_name ?? notif.author_sub} оставил(а) комментарий`
  }
  if (notif.type === 'document_trashed') {
    const title = notif.document_title ? ` «${notif.document_title}»` : ''
    return `${notif.author_display_name ?? notif.author_sub} переместил(а) в корзину${title}`
  }
  if (notif.type === 'calendar_invite') {
    const title = notif.calendar_event_title ? ` «${notif.calendar_event_title}»` : ''
    return `${notif.author_display_name ?? notif.author_sub} пригласил(а) на событие${title}`
  }
  if (notif.type === 'calendar_reminder') {
    const title = notif.calendar_event_title ? ` «${notif.calendar_event_title}»` : ''
    return `Напоминание о событии${title}`
  }
  if (notif.type === 'calendar_event_updated') {
    const title = notif.calendar_event_title ? ` «${notif.calendar_event_title}»` : ''
    return `${notif.author_display_name ?? notif.author_sub} обновил(а) событие${title}`
  }
  if (notif.type === 'calendar_share') {
    const title = notif.calendar_title ? ` «${notif.calendar_title}»` : ''
    return `${notif.author_display_name ?? notif.author_sub} открыл(а) доступ к календарю${title}`
  }
  if (notif.type === 'calendar_event_cancelled') {
    const title =
      notif.calendar_event_title || notif.context_title
        ? ` «${notif.calendar_event_title ?? notif.context_title}»`
        : ''
    return `${notif.author_display_name ?? notif.author_sub} отменил(а) событие${title}`
  }
  if (notif.type === 'calendar_share_revoked') {
    const title =
      notif.calendar_title || notif.context_title
        ? ` «${notif.calendar_title ?? notif.context_title}»`
        : ''
    return `${notif.author_display_name ?? notif.author_sub} отозвал(а) доступ к календарю${title}`
  }
  return 'Новое уведомление'
}

/** Вторая строка в колокольчике: тип сущности (задача, документ, календарь). */
export function notificationEntityLabel(notif: PortalNotification): string {
  if (notif.type === 'document_mention' || notif.type === 'document_trashed') {
    return 'Документ'
  }
  if (notif.type.startsWith('calendar_')) {
    return (
      notif.calendar_event_title ??
      notif.calendar_title ??
      notif.context_title ??
      (notif.calendar_event_id ? 'Событие' : 'Календарь')
    )
  }
  return (
    notif.task_title ??
    (notif.task_id ? `Задача ${notif.task_id.slice(0, 8)}` : 'Задача')
  )
}

/** Формат даты/времени события для мета-строки (всегда МСК). */
export function formatCalendarReminderWhen(iso: string): string {
  const dt = new Date(iso)
  if (Number.isNaN(dt.getTime())) {
    return iso
  }
  const opts: Intl.DateTimeFormatOptions = {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone: 'Europe/Moscow',
  }
  try {
    return `${new Intl.DateTimeFormat('ru-RU', opts).format(dt)} МСК`
  } catch {
    return `${new Intl.DateTimeFormat('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    }).format(dt)} МСК`
  }
}

/** Мета-строка колокольчика: дата/время и место (события календаря). */
export function calendarEventDetailsLine(notif: PortalNotification): string {
  if (
    notif.type !== 'calendar_reminder' &&
    notif.type !== 'calendar_invite' &&
    notif.type !== 'calendar_event_updated'
  ) {
    return ''
  }
  const parts: string[] = []
  if (notif.calendar_event_starts_at) {
    parts.push(formatCalendarReminderWhen(notif.calendar_event_starts_at))
  }
  const loc = notif.calendar_event_location?.trim()
  if (loc) {
    parts.push(loc)
  }
  return parts.join(' · ')
}

/** @deprecated используйте calendarEventDetailsLine */
export function calendarReminderDetailsLine(notif: PortalNotification): string {
  return calendarEventDetailsLine(notif)
}
