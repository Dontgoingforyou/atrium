import {
  filterGuidedTourSteps,
  tourAnchorSelector,
  type GuidedTourStepDef,
  type GuidedTourStepSource,
  type GuidedTourUserContext,
} from '../domain/onboarding/guidedTour'
import { DOCUMENT_TRASH_TTL_DAYS } from '../constants/documentTrash'
import { documentStep, FIRST_DOCUMENT_LINK } from './documentTourSteps'
import { resolveTimesheetGuidedTourSteps } from './stepsTimesheet'

export type { GuidedTourStepDef, GuidedTourUserContext }

const FIRST_CHAT_ROW = tourAnchorSelector('chats-row')

export const GUIDED_TOUR_MVP_STEPS: GuidedTourStepSource[] = [
  {
    id: 'search',
    title: 'Поиск',
    body: 'Ищите информацию по всему порталу — задачи, документы, сообщения, специалистов и события.',
    route: '/',
    selector: tourAnchorSelector('global-search'),
  },
  {
    id: 'advanced-search',
    title: 'Расширенный поиск',
    body: 'На странице поиска доступны режимы «По тексту» и «По смыслу», фильтры типов и тегов.',
    route: '/search',
    selector: tourAnchorSelector('search-mode'),
  },
  {
    id: 'notifications',
    title: 'Уведомления',
    body: 'Здесь появляются уведомления о задачах, упоминаниях, документах и других изменениях, которые относятся к вам.',
    route: '/',
    selector: tourAnchorSelector('notifications'),
    preferPlacement: 'left',
  },
  {
    id: 'theme',
    title: 'Тема',
    body: 'Переключайте оформление портала между светлой и тёмной темой.',
    route: '/',
    selector: tourAnchorSelector('theme-toggle'),
    preferPlacement: 'left',
  },
  {
    id: 'home-favorites',
    title: 'Избранное',
    body: 'Здесь документы, которые вы добавили в избранное, чтобы быстро к ним вернуться.',
    route: '/',
    selector: tourAnchorSelector('home-favorites'),
  },
  {
    id: 'home-my-tasks',
    title: 'Мои задачи',
    body: 'Сводка ваших открытых и просроченных задач прямо на главной.',
    route: '/',
    selector: tourAnchorSelector('home-my-tasks'),
  },
  {
    id: 'home-manager-panel',
    title: 'Панель руководителя',
    body: 'Сводка по задачам доступных разделов: сроки, приоритеты и быстрый переход к задачам команды.',
    route: '/',
    selector: tourAnchorSelector('home-manager-panel'),
    when: (ctx) => ctx.isManagerOrAdmin && !ctx.isPortalAdmin,
  },
  {
    id: 'home-admin-dashboard',
    title: 'Дашборд администратора',
    body: 'Сводка по задачам сотрудников и быстрые действия администратора портала.',
    route: '/',
    selector: tourAnchorSelector('home-admin-dashboard'),
    when: (ctx) => ctx.isPortalAdmin,
  },
  {
    id: 'home-new-task',
    title: 'Новая задача',
    body: 'Создавайте новую задачу прямо с главной страницы.',
    route: '/',
    selector: tourAnchorSelector('home-new-task'),
    when: (ctx) => ctx.isPortalAdmin,
  },
  {
    id: 'home-kanban',
    title: 'Мой канбан',
    body: 'Перейдите к своему канбану, чтобы посмотреть текущие задачи и управлять ими.',
    route: '/',
    selector: tourAnchorSelector('home-kanban'),
  },
  {
    id: 'tasks-scope',
    title: 'Область задач',
    body: 'Переключайтесь между своими задачами и задачами команды.',
    route: '/tasks?view=kanban',
    selector: tourAnchorSelector('tasks-scope'),
    when: (ctx) => ctx.isManagerOrAdmin,
  },
  {
    id: 'tasks-filters',
    title: 'Фильтры',
    body: 'Фильтруйте задачи по статусу, тегам и приоритету.',
    route: '/tasks?view=kanban',
    selector: tourAnchorSelector('tasks-filters'),
  },
  {
    id: 'tasks-view',
    title: 'Представление',
    body: 'Переключайте список и канбан — удобный вид для разных сценариев.',
    route: '/tasks?view=kanban',
    selector: tourAnchorSelector('tasks-view'),
  },
  {
    id: 'tasks-kanban-column-header',
    title: 'Действия колонки',
    body: (ctx) =>
      ctx.isManagerOrAdmin
        ? 'Обычно кнопки скрыты и появляются при наведении на шапку колонки. Сейчас они показаны специально для обучения: «+» — новая задача именно в этой колонке, иконка скачивания — полная выгрузка карточек колонки в .txt (описание, родитель, комментарии), карандаш — название и цвет, крестик — удалить колонку.'
        : 'Обычно кнопки скрыты и появляются при наведении на шапку колонки. Сейчас они показаны специально для обучения: «+» — новая задача именно в этой колонке, иконка скачивания — полная выгрузка карточек колонки в .txt (описание, родитель, комментарии).',
    route: '/tasks?view=kanban',
    selector: tourAnchorSelector('tasks-kanban-column-header'),
    revealHover: true,
  },
  {
    id: 'tasks-kanban-card',
    title: 'Карточка задачи',
    body: (ctx) =>
      ctx.isPortalAdmin
        ? 'Клик или «Открыть» в «⋯» — детали задачи. Администратор может править и перетаскивать любую задачу, а также удалять её через «⋯» / ПКМ. На карточке видны исполнители, теги, срок и подзадачи.'
        : 'Клик или «Открыть» в «⋯» — детали задачи. Автор и исполнитель могут перетаскивать карточку между колонками и править поля; смену исполнителей делает автор. На карточке видны исполнители, теги, срок и подзадачи.',
    route: '/tasks?view=kanban',
    selector: tourAnchorSelector('tasks-kanban-card'),
    revealHover: true,
  },
  {
    id: 'tasks-create',
    title: 'Создать задачу',
    body: 'Отсюда открывается форма создания задачи: название, описание, исполнители и сроки. Статус новой задачи берётся из колонки канбана (или «К выполнению» по умолчанию).',
    route: '/tasks?view=kanban',
    selector: tourAnchorSelector('tasks-create'),
  },
  {
    id: 'tasks-create-form',
    title: 'Поля новой задачи',
    body: (ctx) =>
      ctx.isManagerOrAdmin
        ? 'Форма создания: название, исполнители, приоритет, срок, теги и описание. Сейчас учебный пример — сохранять не нужно; дальше пройдём по полям, затем по секциям карточки. После обучения учебная задача будет удалена.'
        : 'Заполните название и исполнителей — задача создастся автоматически. Можно сразу указать приоритет, срок, теги и описание. Сейчас показан учебный пример; после обучения учебная задача будет удалена.',
    route: '/tasks/new',
    selector: tourAnchorSelector('tasks-create-form'),
    preferPlacement: 'top',
  },
  {
    id: 'tasks-create-title',
    title: 'Название',
    body: 'Обязательное поле. После ввода название задача обычно создаётся автоматически; в обучении форма только для показа.',
    route: '/tasks/new',
    selector: tourAnchorSelector('tasks-create-title'),
    when: (ctx) => ctx.isManagerOrAdmin,
  },
  {
    id: 'tasks-create-assignees',
    title: 'Исполнители',
    body: 'Назначьте хотя бы одного исполнителя — без него задачу создать нельзя.',
    route: '/tasks/new',
    selector: tourAnchorSelector('tasks-create-assignees'),
    when: (ctx) => ctx.isManagerOrAdmin,
  },
  {
    id: 'tasks-create-priority',
    title: 'Приоритет',
    body: 'Низкий, средний или высокий — помогает расставлять порядок в списке и на канбане.',
    route: '/tasks/new',
    selector: tourAnchorSelector('tasks-create-priority'),
    when: (ctx) => ctx.isManagerOrAdmin,
  },
  {
    id: 'tasks-create-due',
    title: 'Срок',
    body: 'Дата дедлайна. Просроченные задачи выделяются в списках и на главной.',
    route: '/tasks/new',
    selector: tourAnchorSelector('tasks-create-due'),
    when: (ctx) => ctx.isManagerOrAdmin,
  },
  {
    id: 'tasks-create-tags',
    title: 'Теги',
    body: 'Общие теги портала — удобно фильтровать задачи и искать по смыслу.',
    route: '/tasks/new',
    selector: tourAnchorSelector('tasks-create-tags'),
    when: (ctx) => ctx.isManagerOrAdmin,
  },
  {
    id: 'tasks-create-description',
    title: 'Описание',
    body: 'Подробности задачи: форматирование, списки и ссылки. Дальше откроем карточку учебной задачи — подзадачи, комментарии, ссылки и файлы.',
    route: '/tasks/new',
    selector: tourAnchorSelector('tasks-create-description'),
    preferPlacement: 'top',
    when: (ctx) => ctx.isManagerOrAdmin,
  },
  {
    id: 'tasks-detail-subtasks',
    title: 'Подзадачи',
    body: 'В карточке задачи можно дробить работу на подзадачи и открывать каждую отдельно.',
    selector: tourAnchorSelector('task-detail-subtasks'),
    preferPlacement: 'left',
    when: (ctx) => ctx.isManagerOrAdmin,
  },
  {
    id: 'tasks-detail-comments',
    title: 'Комментарии',
    body: 'Обсуждение по задаче: комментарии, ответы в ветках и упоминания коллег через @.',
    selector: tourAnchorSelector('task-detail-comments'),
    preferPlacement: 'top',
    when: (ctx) => ctx.isManagerOrAdmin,
  },
  {
    id: 'tasks-detail-links',
    title: 'Ссылки',
    body: 'Внешние ссылки по задаче — документы, тикеты, материалы вне портала.',
    selector: tourAnchorSelector('task-detail-links'),
    preferPlacement: 'top',
    when: (ctx) => ctx.isManagerOrAdmin,
  },
  {
    id: 'tasks-detail-files',
    title: 'Файлы',
    body: 'Вложения к задаче: загрузка, просмотр и удаление своих файлов.',
    selector: tourAnchorSelector('task-detail-files'),
    preferPlacement: 'top',
    when: (ctx) => ctx.isManagerOrAdmin,
  },
  {
    id: 'nav-specialists',
    title: 'Специалисты',
    body: (ctx) =>
      ctx.isPortalAdmin
        ? 'Воронка специалистов: доска, карточки и настройки колонок. Администратор может добавлять и менять колонки.'
        : 'Раздел для ведения специалистов и работы менеджеров с воронкой.',
    route: '/',
    selector: tourAnchorSelector('nav-specialists'),
    when: (ctx) => ctx.isManagerOrAdmin,
  },
  {
    id: 'specialists-scope',
    title: 'Область специалистов',
    body: 'Переключайтесь между своими специалистами и общей доской.',
    route: '/specialists?view=kanban',
    selector: tourAnchorSelector('specialists-scope'),
    when: (ctx) => ctx.isManagerOrAdmin,
  },
  {
    id: 'specialists-filters',
    title: 'Фильтры специалистов',
    body: 'Фильтруйте доску по менеджерам и специалистам.',
    route: '/specialists?view=kanban',
    selector: tourAnchorSelector('specialists-filters'),
    when: (ctx) => ctx.isManagerOrAdmin,
  },
  {
    id: 'specialists-view',
    title: 'Вид специалистов',
    body: 'Канбан или список — выберите удобный формат просмотра.',
    route: '/specialists?view=kanban',
    selector: tourAnchorSelector('specialists-view'),
    when: (ctx) => ctx.isManagerOrAdmin,
  },
  {
    id: 'specialists-kanban',
    title: 'Канбан специалистов',
    body: (ctx) =>
      ctx.isPortalAdmin
        ? 'Карточки по колонкам воронки. Откройте карточку — профиль, комментарии, Jira. Администратор может добавлять и править колонки доски.'
        : 'Карточки специалистов по колонкам воронки. Откройте карточку, чтобы увидеть профиль, комментарии и связи с Jira.',
    route: '/specialists?view=kanban',
    selector: tourAnchorSelector('specialists-kanban'),
    when: (ctx) => ctx.isManagerOrAdmin,
  },
  {
    id: 'specialists-kanban-column-header',
    title: 'Действия колонки',
    body: (ctx) =>
      ctx.isPortalAdmin
        ? 'Обычно кнопки скрыты и появляются при наведении на шапку колонки. Сейчас они показаны специально для обучения: «+» — добавить специалиста именно в эту колонку, карандаш — название и цвет, крестик — удалить колонку.'
        : 'Обычно кнопка «+» скрыта и появляется при наведении на шапку колонки. Сейчас она показана специально для обучения: «+» — добавить специалиста именно в эту колонку воронки.',
    route: '/specialists?view=kanban',
    selector: tourAnchorSelector('specialists-kanban-column-header'),
    revealHover: true,
    when: (ctx) => ctx.isManagerOrAdmin,
  },
  {
    id: 'specialists-kanban-card',
    title: 'Карточка специалиста',
    body: (ctx) =>
      ctx.isPortalAdmin
        ? 'Клик по карточке открывает профиль. Карточку можно перетаскивать между колонками воронки. Администратор управляет колонками доски.'
        : 'Клик по карточке открывает профиль. Свою карточку можно перетаскивать между колонками воронки.',
    route: '/specialists?view=kanban',
    selector: tourAnchorSelector('specialists-kanban-card'),
    revealHover: true,
    when: (ctx) => ctx.isManagerOrAdmin,
  },
  {
    id: 'specialists-detail',
    title: 'Профиль специалиста',
    body: (ctx) =>
      ctx.isPortalAdmin
        ? 'Открытая карточка: профиль, ссылки, комментарии, менеджеры и Jira. Удаление специалиста доступно только администратору. Закройте окно крестиком или кликом по фону.'
        : 'Открытая карточка: профиль, ссылки, комментарии и менеджеры. При наличии прав доступен блок Jira. Закройте окно крестиком или кликом по фону.',
    route: '/specialists?view=kanban',
    selector: tourAnchorSelector('specialists-detail'),
    preferPlacement: 'top',
    when: (ctx) => ctx.isManagerOrAdmin,
  },
  {
    id: 'nav-chats',
    title: 'Чаты',
    body: 'Личные и групповые переписки внутри портала.',
    route: '/',
    selector: tourAnchorSelector('nav-chats'),
  },
  {
    id: 'chats-sidebar',
    title: 'Список чатов',
    body: 'Слева — ваши диалоги и группы. Нажмите на чат, чтобы открыть переписку справа.',
    route: '/chats',
    selector: tourAnchorSelector('chats-sidebar'),
  },
  {
    id: 'chats-new',
    title: 'Новый чат',
    body: '«+ Диалог» — личная переписка с коллегой. «+ Группа» — чат на несколько участников с названием.',
    route: '/chats',
    selector: tourAnchorSelector('chats-new'),
  },
  {
    id: 'chats-row',
    title: 'Меню чата',
    body: 'Правый клик по чату в списке открывает меню действий, в том числе удаление диалога. Сейчас меню показано для обучения — учебный чат можно удалить после тура.',
    route: '/chats',
    selector: FIRST_CHAT_ROW,
  },
  {
    id: 'chats-thread-header',
    title: 'Шапка переписки',
    body: 'Здесь название чата, управление уведомлениями и меню «⋮» с настройками группы (участники, аватар).',
    route: '/chats',
    openFromSelector: FIRST_CHAT_ROW,
    selector: tourAnchorSelector('chats-thread-header'),
  },
  {
    id: 'chats-messages',
    title: 'Сообщения',
    body: 'Правый клик по сообщению открывает меню: эмодзи-реакции, ответить, переслать, изменить своё, закрепить, удалить только у себя или у всех. Внизу меню — кто просмотрел. Сейчас меню показано для обучения; кнопка «⋯» у своего сообщения обычно видна только при наведении.',
    route: '/chats',
    openFromSelector: FIRST_CHAT_ROW,
    selector: tourAnchorSelector('chats-message-row'),
    revealHover: true,
  },
  {
    id: 'chats-emoji-easter',
    title: 'Эмодзи в чате',
    body: '...тёдйозиорп ьдубин-отч оньлетазябо от издомэ ан ьтажан илсе отч тяровог...',
    route: '/chats',
    openFromSelector: FIRST_CHAT_ROW,
    selector: tourAnchorSelector('chats-emoji-easter'),
  },
  {
    id: 'chats-composer',
    title: 'Поле ввода',
    body: 'Пишите текст, прикрепляйте файлы, вставляйте эмодзи, записывайте голос и отмечайте коллег через @. При ответе над полем появляется цитата — её можно отменить крестиком.',
    route: '/chats',
    openFromSelector: FIRST_CHAT_ROW,
    selector: tourAnchorSelector('chats-composer'),
    preferPlacement: 'top',
  },
  {
    id: 'nav-calendar',
    title: 'Календарь',
    body: 'События, встречи и общие календари команды.',
    route: '/',
    selector: tourAnchorSelector('nav-calendar'),
  },
  {
    id: 'calendar-sidebar',
    title: 'Мои календари',
    body: 'Включайте и выключайте свои календари галочками — на сетке останутся только выбранные. Можно переименовать и сменить цвет.',
    route: '/calendar',
    selector: tourAnchorSelector('calendar-sidebar'),
  },
  {
    id: 'calendar-create-calendar',
    title: 'Новый календарь',
    body: 'Создайте отдельный календарь под проект или тип встреч — он появится в списке слева.',
    route: '/calendar',
    selector: tourAnchorSelector('calendar-create-calendar'),
  },
  {
    id: 'calendar-toolbar',
    title: 'Навигация по месяцам',
    body: 'Кнопки «Сегодня», стрелки и название месяца переключают период на сетке.',
    route: '/calendar',
    selector: tourAnchorSelector('calendar-toolbar'),
  },
  {
    id: 'calendar-peer-picker',
    title: 'Календарь участника',
    body: 'Выберите коллегу, чтобы посмотреть его события. Свои календари при этом временно скрываются с сетки. Крестик у выбранного человека возвращает свой календарь.',
    route: '/calendar',
    selector: tourAnchorSelector('calendar-peer-picker'),
  },
  {
    id: 'calendar-create-event',
    title: 'Создать событие',
    body: 'Откроется форма: название, время, календарь, участники и напоминания. Сохраните — событие появится на сетке.',
    route: '/calendar',
    selector: tourAnchorSelector('calendar-create-event'),
  },
  {
    id: 'calendar-event',
    title: 'Событие на сетке',
    body: 'Цветная полоска — учебное событие на сегодня. Клик открывает карточку. После обучения учебное событие будет удалено.',
    route: '/calendar',
    selector: tourAnchorSelector('calendar-event'),
  },
  {
    id: 'calendar-event-detail',
    title: 'Карточка события',
    body: 'Здесь название, время, место, описание, участники и напоминания. Можно изменить или удалить событие.',
    route: '/calendar',
    selector: tourAnchorSelector('calendar-event-detail'),
  },
  {
    id: 'calendar-event-edit-form',
    title: 'Редактирование события',
    body: 'Форма изменения: название, начало и конец, цвет, повтор, место, описание, участники и напоминания. Сейчас показан учебный пример — сохранять не нужно; после обучения учебное событие будет удалено.',
    route: '/calendar',
    selector: tourAnchorSelector('calendar-event-edit-form'),
  },
  {
    id: 'calendar-grid',
    title: 'Сетка месяца',
    body: 'Клик по дню создаёт событие на эту дату. Клик по цветной полоске события открывает карточку с деталями и действиями.',
    route: '/calendar',
    selector: tourAnchorSelector('calendar-grid'),
  },
  {
    id: 'calendar-day-cell',
    title: 'День на сетке',
    body: 'Сегодняшний день подсвечен. Нажмите на пустое место в ячейке, чтобы быстро создать событие.',
    route: '/calendar',
    selector: tourAnchorSelector('calendar-day-cell'),
  },
  {
    id: 'nav-tags',
    title: 'Теги',
    body: 'Общие теги для задач, документов и поиска.',
    route: '/',
    selector: tourAnchorSelector('nav-tags'),
  },
  {
    id: 'tags-table',
    title: 'Список тегов',
    body: 'Все теги портала. По ним удобно фильтровать поиск и сущности. Можно посмотреть, где тег используется.',
    route: '/tags',
    selector: tourAnchorSelector('tags-table'),
  },
  {
    id: 'tags-create',
    title: 'Создать тег',
    body: (ctx) =>
      ctx.isPortalAdmin
        ? 'Администратор может создавать теги для всего портала: задайте название и цвет.'
        : 'Менеджер может создавать теги: задайте название и цвет — тег сразу появится в списке.',
    route: '/tags',
    selector: tourAnchorSelector('tags-create'),
    when: (ctx) => ctx.isManagerOrAdmin,
  },
  {
    id: 'nav-analytics',
    title: 'Аналитика',
    body: (ctx) =>
      ctx.isManagerOrAdmin
        ? 'Таймшиты команды, отчёты по трудозатратам и бенч.'
        : 'Таймшиты и отчёты по работе портала.',
    route: '/',
    selector: tourAnchorSelector('nav-analytics'),
  },
  {
    id: 'analytics-tabs',
    title: 'Разделы аналитики',
    body: (ctx) =>
      ctx.isManagerOrAdmin
        ? '«Таймшиты» — часы специалистов. «Отчёты» — сводка трудозатрат за период. «Бенч» — воронка найма.'
        : '«Таймшиты» — часы за текущий месяц. «Отчёты» — сводка трудозатрат за период.',
    route: '/analytics/timesheets',
    selector: tourAnchorSelector('analytics-tabs'),
  },
  {
    id: 'analytics-summary-timesheets',
    title: 'Таймшиты: текущий месяц',
    body: 'Часы и число записей за текущий месяц.',
    route: '/analytics/timesheets',
    selector: tourAnchorSelector('analytics-summary-timesheets'),
  },
  {
    id: 'analytics-timesheets-month',
    title: 'Таймшиты команды',
    body: 'Выберите месяц — ниже появится список специалистов с суммой часов. Раскройте карточку, чтобы увидеть записи по дням.',
    route: '/analytics/timesheets',
    selector: tourAnchorSelector('analytics-timesheets-month'),
    when: (ctx) => ctx.isManagerOrAdmin,
  },
  {
    id: 'analytics-timesheets-list',
    title: 'Список специалистов',
    body: 'Сортировка по имени, экспорт и детализация по каждому специалисту за выбранный месяц.',
    route: '/analytics/timesheets',
    selector: tourAnchorSelector('analytics-timesheets-list'),
    when: (ctx) => ctx.isManagerOrAdmin,
  },
  {
    id: 'analytics-reports-filters',
    title: 'Фильтры отчёта',
    body: 'Укажите период (месяц или точные даты) и группировку — по неделям или месяцам.',
    route: '/analytics/reports',
    selector: tourAnchorSelector('analytics-reports-filters'),
  },
  {
    id: 'analytics-reports-table',
    title: 'Таблица отчёта',
    body: 'Сводка трудозатрат по выбранному периоду. Используйте фильтры выше, чтобы сузить данные.',
    route: '/analytics/reports',
    selector: tourAnchorSelector('analytics-reports-table'),
  },
  {
    id: 'nav-trash',
    title: 'Корзина',
    body: (ctx) =>
      ctx.isPortalAdmin
        ? 'Удалённые документы можно восстановить или удалить окончательно.'
        : 'Удалённые документы можно восстановить.',
    route: '/',
    selector: tourAnchorSelector('nav-trash'),
    when: (ctx) => ctx.isManagerOrAdmin,
  },
  {
    id: 'trash-hint',
    title: 'Срок хранения',
    body: (ctx) =>
      ctx.isPortalAdmin
        ? `Документы в корзине хранятся ${DOCUMENT_TRASH_TTL_DAYS} дней, затем удаляются безвозвратно. После «Восстановить» или «Удалить навсегда» несколько секунд можно отменить действие.`
        : `Документы в корзине хранятся ${DOCUMENT_TRASH_TTL_DAYS} дней, затем удаляются безвозвратно. После «Восстановить» несколько секунд можно отменить действие.`,
    route: '/p/trash',
    selector: tourAnchorSelector('trash-hint'),
    when: (ctx) => ctx.isManagerOrAdmin,
  },
  {
    id: 'trash-list',
    title: 'Документы в корзине',
    body: (ctx) =>
      ctx.isPortalAdmin
        ? 'У каждого документа — кто удалил, когда и сколько дней осталось. «Восстановить» вернёт документ; «Удалить навсегда» доступно только администратору.'
        : 'У каждого документа — кто удалил, когда и сколько дней осталось. «Восстановить» вернёт документ в дерево меню.',
    route: '/p/trash',
    selector: tourAnchorSelector('trash-list'),
    when: (ctx) => ctx.isManagerOrAdmin,
  },
  {
    id: 'trash-purge',
    title: 'Удалить навсегда',
    body: 'Кнопка окончательного удаления доступна только администратору. Восстановить такой документ будет нельзя.',
    route: '/p/trash',
    selector: tourAnchorSelector('trash-purge'),
    when: (ctx) => ctx.isPortalAdmin,
  },
  {
    id: 'nav-admin',
    title: 'Панель администратора',
    body: 'Отдельная панель внутренних настроек портала — доступно только администратору. Открывается в своём контуре — пользуйтесь ей, когда нужны системные изменения.',
    route: '/',
    selector: tourAnchorSelector('nav-admin'),
    when: (ctx) => ctx.isPortalAdmin,
  },
  documentStep('nav-documents', {
    body: 'Дерево документов в левом меню. Раскрывайте ветки и открывайте нужный документ кликом по названию.',
    route: '/',
  }),
  {
    id: 'documents-create',
    title: 'Создать документ',
    body: (ctx) =>
      ctx.isPortalAdmin
        ? 'Кнопка «+» у секции создаёт документ. Администратор и менеджер могут создавать и править документы в дереве.'
        : 'Кнопка «+» у секции создаёт новый документ в этой ветке и сразу открывает его для редактирования.',
    route: '/',
    selector: tourAnchorSelector('documents-create'),
    when: (ctx) => ctx.isManagerOrAdmin,
  },
  documentStep('document-title', {
    body: (ctx) =>
      ctx.isManagerOrAdmin
        ? 'Название можно изменить кликом. Рядом — избранное и меню действий: история версий, удаление и другое.'
        : 'Заголовок документа и избранное. Редактирование доступно менеджерам и администраторам.',
    openFromSelector: FIRST_DOCUMENT_LINK,
  }),
  {
    id: 'document-tags',
    title: 'Теги документа',
    body: (ctx) =>
      ctx.isManagerOrAdmin
        ? 'Теги помогают искать документ. Нажмите на блок, чтобы добавить или убрать теги.'
        : 'Теги документа помогают в поиске. Изменять их могут менеджеры и администраторы.',
    openFromSelector: FIRST_DOCUMENT_LINK,
    selector: tourAnchorSelector('document-tags'),
  },
  documentStep('document-body', {
    body: (ctx) =>
      ctx.isManagerOrAdmin
        ? 'Основной текст. При редактировании — панель форматирования: заголовки, списки, таблицы, ссылки и изображения.'
        : 'Основной текст документа. Редактирование и панель форматирования доступны менеджерам и администраторам.',
    openFromSelector: FIRST_DOCUMENT_LINK,
  }),
  documentStep('document-comments', {
    body: 'Обсуждайте документ справа: оставляйте комментарии, отвечайте в ветках и упоминайте коллег через @.',
    openFromSelector: FIRST_DOCUMENT_LINK,
  }),
  {
    id: 'account-restart',
    title: 'Обучение',
    body: 'Позже обучение можно пройти снова кнопкой на этой странице.',
    route: '/account',
    selector: tourAnchorSelector('account-restart-tour'),
    preferPlacement: 'top',
  },
]

export function resolveGuidedTourSteps(ctx: GuidedTourUserContext): GuidedTourStepDef[] {
  if (ctx.isTimesheetOnly) {
    return resolveTimesheetGuidedTourSteps(ctx)
  }
  return filterGuidedTourSteps(GUIDED_TOUR_MVP_STEPS, ctx)
}
