import { describe, expect, it } from 'vitest'
import {
  calendarEventDetailsLine,
  calendarReminderDetailsLine,
  notificationEntityLabel,
  notificationPrimaryLine,
} from '@/domain/notifications/notificationLabels'
import type { PortalNotification } from '@/types/notification'

const NOTIF_BASE: PortalNotification = {
  id: 'n1',
  type: 'task_mention',
  recipient_sub: 'user-1',
  author_sub: 'user-2',
  created_at: '2026-06-01T12:00:00Z',
  read_at: null,
  task_id: null,
  comment_id: null,
  document_id: null,
  document_comment_id: null,
  task_title: null,
  task_priority: null,
  task_due_at: null,
  task_status: null,
  document_title: null,
  author_display_name: null,
}

function baseNotif(overrides: Partial<PortalNotification>): PortalNotification {
  return { ...NOTIF_BASE, ...overrides }
}

describe('notificationEntityLabel', () => {
  it('document_trashed без task_id — «Документ», не «Задача»', () => {
    const label = notificationEntityLabel(
      baseNotif({
        type: 'document_trashed',
        document_id: 'doc-1',
        document_title: 'Без названия',
        task_id: null,
        task_title: null,
      }),
    )
    expect(label).toBe('Документ')
    expect(label).not.toBe('Задача')
  })

  it('document_mention — «Документ»', () => {
    expect(
      notificationEntityLabel(
        baseNotif({
          type: 'document_mention',
          document_id: 'doc-1',
          document_title: 'Тест',
        }),
      ),
    ).toBe('Документ')
  })

  it('task_mention без title — fallback «Задача»', () => {
    expect(
      notificationEntityLabel(
        baseNotif({
          type: 'task_mention',
          task_id: 'task-abc',
          task_title: null,
        }),
      ),
    ).toBe('Задача task-abc')
  })

  it('calendar_event_cancelled — context_title как подпись сущности', () => {
    expect(
      notificationEntityLabel(
        baseNotif({
          type: 'calendar_event_cancelled',
          calendar_event_id: null,
          context_title: 'Стендап',
        }),
      ),
    ).toBe('Стендап')
  })
})

describe('notificationPrimaryLine', () => {
  it('task_due_soon — срок через 2 дня', () => {
    expect(
      notificationPrimaryLine(
        baseNotif({
          type: 'task_due_soon',
          task_id: 'task-1',
          task_title: 'Отчёт',
        }),
      ),
    ).toBe('Срок задачи через 2 дня')
  })

  it('task_overdue — задача просрочена', () => {
    expect(
      notificationPrimaryLine(
        baseNotif({
          type: 'task_overdue',
          task_id: 'task-1',
          task_title: 'Отчёт',
        }),
      ),
    ).toBe('Задача просрочена')
  })

  it('неизвестный type — запасная строка', () => {
    expect(notificationPrimaryLine(baseNotif({ type: 'unknown_kind' }))).toBe('Новое уведомление')
  })

  it('task_comment — автор оставил комментарий', () => {
    expect(
      notificationPrimaryLine(
        baseNotif({
          type: 'task_comment',
          author_display_name: 'Руководитель',
          task_id: 'task-1',
          task_title: 'Статус',
        }),
      ),
    ).toBe('Руководитель оставил(а) комментарий')
  })

  it('calendar_share_revoked использует context_title', () => {
    expect(
      notificationPrimaryLine(
        baseNotif({
          type: 'calendar_share_revoked',
          author_display_name: 'Анна',
          context_title: 'Команда',
        }),
      ),
    ).toBe('Анна отозвал(а) доступ к календарю «Команда»')
  })

  it('calendar_event_cancelled использует context_title', () => {
    expect(
      notificationPrimaryLine(
        baseNotif({
          type: 'calendar_event_cancelled',
          author_display_name: 'Иван',
          context_title: 'Ретро',
        }),
      ),
    ).toBe('Иван отменил(а) событие «Ретро»')
  })
})

describe('calendarEventDetailsLine', () => {
  it('собирает дату/время и место для reminder в МСК', () => {
    const line = calendarEventDetailsLine(
      baseNotif({
        type: 'calendar_reminder',
        calendar_event_title: 'Стендап',
        calendar_event_starts_at: '2026-08-06T10:00:00Z',
        calendar_event_timezone: 'UTC',
        calendar_event_location: 'https://telemost.yandex.ru/j/1',
      }),
    )
    expect(line).toContain('telemost.yandex.ru')
    expect(line).toContain('МСК')
    expect(line).toMatch(/06\.08\.2026/)
    expect(line).toMatch(/13:00/)
  })

  it('для invite тоже показывает when/location в МСК', () => {
    const line = calendarEventDetailsLine(
      baseNotif({
        type: 'calendar_invite',
        calendar_event_starts_at: '2026-08-06T10:00:00Z',
        calendar_event_timezone: 'UTC',
        calendar_event_location: 'Офис',
      }),
    )
    expect(line).toContain('Офис')
    expect(line).toContain('МСК')
    expect(line).toMatch(/13:00/)
  })

  it('для других типов — пустая строка', () => {
    expect(calendarEventDetailsLine(baseNotif({ type: 'task_assigned' }))).toBe('')
  })

  it('calendarReminderDetailsLine — алиас', () => {
    const n = baseNotif({
      type: 'calendar_reminder',
      calendar_event_starts_at: '2026-08-06T10:00:00Z',
      calendar_event_location: 'A',
    })
    expect(calendarReminderDetailsLine(n)).toBe(calendarEventDetailsLine(n))
  })
})
