/**
 * Колоцированные query-ключи домена «специалисты» для детальной карточки и модалки добавления.
 *
 * Используются деревом маршрута /specialists (компоненты в components/specialists/
 * и страницы в pages/specialists/). Ключи доски/колонок/pref живут в
 * domain/specialists/specialistBoardCache.ts (QK_BOARD_ROOT, QK_COLUMNS, QK_PREF).
 *
 * Назначение: единый источник для инвалидации кэша, чтобы не плодить строковые
 * литералы вроде ['specialists','links',sub] по компонентам.
 */

/** Ссылки специалиста (CV, портфолио и т.д.). */
export const specialistLinksQueryKey = (specialistSub: string) =>
  ['specialists', 'links', specialistSub] as const

/** Заметки менеджера о специалисте. */
export const specialistNotesQueryKey = (specialistSub: string) =>
  ['specialists', 'notes', specialistSub] as const

/** Состояние Jira-привязки специалиста. */
export const specialistJiraQueryKey = (specialistSub: string) =>
  ['specialists', 'jira', specialistSub] as const

/** Поиск карточек специалиста в Jira по ФИО. */
export const specialistJiraSearchQueryKey = (query: string) =>
  ['specialists', 'jira-search', query] as const

/** Расширенный профиль специалиста (персональные данные). */
export const specialistProfileQueryKey = (specialistSub: string) =>
  ['specialists', 'profile', specialistSub] as const

/** Менеджеры, за которыми закреплён специалист (drawer-панель). */
export const specialistManagersQueryKey = (specialistSub: string) =>
  ['specialists', 'by-specialist', specialistSub] as const

/** Студенты-специалисты для модалки добавления на доску. */
export const specialistStudentsModalQueryKey = () =>
  ['portal', 'users', 'specialists-students', 'add-modal'] as const

/** Студенты-специалисты для пикера-фильтра (опции мульти-выбора). */
export const specialistStudentsFilterQueryKey = () =>
  ['portal', 'users', 'specialists-students', 'filter-options'] as const

/** Корень ключей студентов-специалистов (для инвалидации префиксом: modal + filter). */
export const SPECIALISTS_STUDENTS_ROOT_QUERY_KEY = ['portal', 'users', 'specialists-students'] as const

/** Список специалистов портала (доска/листинг). */
export const SPECIALISTS_LIST_QUERY_KEY = ['portal', 'specialists'] as const

/** Корень для инвалидации префиксом всех детальных ключей специалиста. */
export const SPECIALISTS_DETAIL_ROOT_QUERY_KEY = ['specialists'] as const
