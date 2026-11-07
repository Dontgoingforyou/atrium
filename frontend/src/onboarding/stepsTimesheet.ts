import {
  filterGuidedTourSteps,
  tourAnchorSelector,
  type GuidedTourStepSource,
} from '../domain/onboarding/guidedTour'
import { documentStep } from './documentTourSteps'

/** Guided tour для timesheet-only (Специалисты АУ, students). */
export const GUIDED_TOUR_TIMESHEET_STEPS: GuidedTourStepSource[] = [
  {
    id: 'theme',
    title: 'Тема',
    body: 'Переключайте оформление портала между светлой и тёмной темой.',
    route: '/analytics/timesheets',
    selector: tourAnchorSelector('theme-toggle'),
    preferPlacement: 'left',
  },
  {
    id: 'nav-timesheets',
    title: 'Таймшиты',
    body: 'Основной раздел для учёта рабочего времени: записи по дням, отчёты и импорт из Jira.',
    route: '/analytics/timesheets',
    selector: tourAnchorSelector('nav-timesheets'),
  },
  {
    id: 'timesheets-actions',
    title: 'Действия',
    body: '«+ Добавить запись» — одна запись за день. «Массовое добавление» — несколько дней сразу. «Импорт из Jira» — загрузка CSV выгрузки.',
    route: '/analytics/timesheets',
    selector: tourAnchorSelector('analytics-timesheets-actions'),
  },
  {
    id: 'timesheets-filters',
    title: 'Период',
    body: 'Укажите даты «С» и «По», чтобы отфильтровать список записей и сводку часов.',
    route: '/analytics/timesheets',
    selector: tourAnchorSelector('timesheets-filters'),
  },
  {
    id: 'timesheets-summary',
    title: 'Сводка',
    body: 'Итого часов и число записей за выбранный период — обновляется при смене фильтров.',
    route: '/analytics/timesheets',
    selector: tourAnchorSelector('timesheets-summary'),
  },
  {
    id: 'timesheets-tabs',
    title: 'Вкладки',
    body: '«Записи» — список по дням. «Отчёт по периодам» — группировка по неделям или месяцам.',
    route: '/analytics/timesheets',
    selector: tourAnchorSelector('timesheets-tabs'),
  },
  {
    id: 'timesheets-entries',
    title: 'Список записей',
    body: 'Записи сгруппированы по дням. У каждой есть три действия: изменить, дублировать или удалить. Для обучения мы добавили учебные записи — их можно удалить после тура.',
    route: '/analytics/timesheets',
    selector: tourAnchorSelector('timesheets-entries'),
  },
  {
    id: 'timesheets-report',
    title: 'Отчёт по периодам',
    body: 'Сводка трудозатрат по неделям или месяцам за выбранный период. Переключайте группировку в фильтре отчёта.',
    route: '/analytics/timesheets?tab=report',
    selector: tourAnchorSelector('timesheets-report'),
  },
  documentStep('nav-documents', {
    body: 'Регламенты и материалы для разработчиков в левом меню. Для обучения добавлен «Учебный документ».',
    route: '/analytics/timesheets',
  }),
  documentStep('document-title', {
    body: 'Название открытого документа. Рядом — избранное для быстрого возврата.',
  }),
  documentStep('document-body', {
    body: 'Основной текст документа. Редактирование доступно менеджерам и администраторам — вы работаете в режиме просмотра.',
  }),
  documentStep('document-comments', {
    body: 'Обсуждайте документ справа: оставляйте комментарии, отвечайте в ветках и упоминайте коллег через @.',
  }),
  {
    id: 'nav-guided-tour',
    title: 'Обучение',
    body: 'Позже тур можно пройти снова кнопкой «Обучение» в левом меню.',
    route: '/analytics/timesheets',
    selector: tourAnchorSelector('nav-guided-tour'),
    preferPlacement: 'right',
  },
]

export function resolveTimesheetGuidedTourSteps(
  ctx: Parameters<typeof filterGuidedTourSteps>[1],
) {
  return filterGuidedTourSteps(GUIDED_TOUR_TIMESHEET_STEPS, ctx)
}
