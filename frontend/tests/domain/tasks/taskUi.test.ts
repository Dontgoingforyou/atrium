import { describe, expect, it } from 'vitest'
import {
  DONE_THIS_MONTH_FILTER_LABEL,
  DONE_THIS_MONTH_FILTER_SELECTED_LABEL,
  KPI_OPEN_FILTER_LABEL,
  KPI_OPEN_FILTER_SELECTED_LABEL,
  NO_ASSIGNEE_FILTER_LABEL,
  NO_ASSIGNEE_FILTER_SELECTED_LABEL,
  OVERDUE_FILTER_LABEL,
  OVERDUE_FILTER_SELECTED_LABEL,
  PRIORITY_COLOR,
  PRIORITY_LABELS,
  STATUS_COLOR,
  STATUS_LABELS,
  TASK_STATUS_ORDER,
} from '../../../src/domain/tasks/taskUi'

describe('TASK_STATUS_ORDER', () => {
  it('содержит все четыре статуса задачи', () => {
    expect(TASK_STATUS_ORDER).toEqual(['todo', 'in_progress', 'done', 'cancelled'])
  })
})

describe('STATUS_LABELS', () => {
  it('содержит метки для всех статусов', () => {
    expect(STATUS_LABELS.todo).toBe('К выполнению')
    expect(STATUS_LABELS.in_progress).toBe('В работе')
    expect(STATUS_LABELS.done).toBe('Завершена')
    expect(STATUS_LABELS.cancelled).toBe('Отменена')
  })
})

describe('OVERDUE_FILTER_LABEL', () => {
  it('короткая подпись чипа без «всей команды»', () => {
    expect(OVERDUE_FILTER_LABEL).toBe('Просроченные задачи')
    expect(OVERDUE_FILTER_SELECTED_LABEL).toBe('да')
    expect(OVERDUE_FILTER_SELECTED_LABEL).not.toMatch(/всей команды/)
  })
})

describe('dashboard drilldown filter labels', () => {
  it('подписи чипов совпадают с плашками дашборда', () => {
    expect(KPI_OPEN_FILTER_LABEL).toBe('Открытые задачи')
    expect(KPI_OPEN_FILTER_SELECTED_LABEL).toBe('да')
    expect(DONE_THIS_MONTH_FILTER_LABEL).toBe('Закрыто в этом месяце')
    expect(DONE_THIS_MONTH_FILTER_SELECTED_LABEL).toBe('да')
    expect(NO_ASSIGNEE_FILTER_LABEL).toBe('Без исполнителя')
    expect(NO_ASSIGNEE_FILTER_SELECTED_LABEL).toBe('да')
  })
})

describe('PRIORITY_LABELS', () => {
  it('содержит метки для всех приоритетов', () => {
    expect(PRIORITY_LABELS.low).toBe('Низкий')
    expect(PRIORITY_LABELS.medium).toBe('Обычный')
    expect(PRIORITY_LABELS.high).toBe('Высокий')
  })
})

describe('STATUS_COLOR', () => {
  it('возвращает CSS-переменные для всех статусов', () => {
    for (const status of TASK_STATUS_ORDER) {
      expect(STATUS_COLOR[status]).toMatch(/^var\(--/)
    }
  })

  it('todo и in_progress имеют разные цвета', () => {
    expect(STATUS_COLOR.todo).not.toBe(STATUS_COLOR.in_progress)
  })
})

describe('PRIORITY_COLOR', () => {
  it('возвращает CSS-переменные для всех приоритетов', () => {
    for (const priority of ['low', 'medium', 'high'] as const) {
      expect(PRIORITY_COLOR[priority]).toMatch(/^var\(--/)
    }
  })

  it('high имеет отдельный цвет опасности', () => {
    expect(PRIORITY_COLOR.high).toContain('danger')
  })
})
