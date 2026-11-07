import type { TaskPriority, TaskStatus } from '../../types/task'

export const TASK_STATUS_ORDER: TaskStatus[] = ['todo', 'in_progress', 'done', 'cancelled']

export const STATUS_LABELS: Record<TaskStatus, string> = {
  todo: 'К выполнению',
  in_progress: 'В работе',
  done: 'Завершена',
  cancelled: 'Отменена',
}

export const PRIORITY_LABELS: Record<TaskPriority, string> = {
  low: 'Низкий',
  medium: 'Обычный',
  high: 'Высокий',
}

export const STATUS_COLOR: Record<TaskStatus, string> = {
  todo: 'var(--color-accent)',
  in_progress: 'var(--color-warning)',
  done: 'var(--color-success)',
  cancelled: 'var(--color-text-disabled)',
}

export const PRIORITY_COLOR: Record<TaskPriority, string> = {
  low: 'var(--color-text-disabled)',
  medium: 'var(--color-warning)',
  high: 'var(--color-danger-ui)',
}

export const OVERDUE_FILTER_LABEL = 'Просроченные задачи'
export const OVERDUE_FILTER_SELECTED_LABEL = 'да'
export const KPI_OPEN_FILTER_LABEL = 'Открытые задачи'
export const KPI_OPEN_FILTER_SELECTED_LABEL = 'да'
export const DONE_THIS_MONTH_FILTER_LABEL = 'Закрыто в этом месяце'
export const DONE_THIS_MONTH_FILTER_SELECTED_LABEL = 'да'
export const NO_ASSIGNEE_FILTER_LABEL = 'Без исполнителя'
export const NO_ASSIGNEE_FILTER_SELECTED_LABEL = 'да'
