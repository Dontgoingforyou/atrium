/**
 * Общие лейблы и константы домена документов.
 *
 * Единый источник для строк, которые раньше были размазаны магическими литералами
 * по компонентам `components/documents/*` и `pages/documents/*`.
 */

/** Подпись документа без заголовка. Раньше литерал 'Без названия' дублировался в 4+ файлах. */
export const UNTITLED_DOCUMENT_LABEL = 'Без названия'

/** Статусы документа (контракт с бэкендом `portal_document.status`). */
export const DOCUMENT_STATUS_DRAFT = 'draft'
export const DOCUMENT_STATUS_ACTIVE = 'active'
export const DOCUMENT_STATUS_ARCHIVED = 'archived'

export const DOCUMENT_STATUS_LABELS: Record<string, string> = {
  [DOCUMENT_STATUS_DRAFT]: 'Черновик',
  [DOCUMENT_STATUS_ACTIVE]: 'Опубликован',
  [DOCUMENT_STATUS_ARCHIVED]: 'В архиве',
}

/**
 * Сигнальное значение diff для `tag_ids`: бэкенд не присылает полный список тегов
 * в old/new, а заменяет его маркером `replaced`. Фронт показывает «обновлены».
 */
export const TAG_IDS_REPLACED = 'replaced'
export const TAG_IDS_REPLACED_LABEL = 'обновлены'

/** Лейблы событий истории документов (поле `action` в diff). */
export const DOCUMENT_ACTION_LABELS: Record<string, string> = {
  created: 'Документ создан',
}
