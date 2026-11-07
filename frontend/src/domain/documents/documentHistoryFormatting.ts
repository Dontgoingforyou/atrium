/**
 * Форматирование записей истории документа для презентационного слоя.
 *
 * Вынесено из `components/documents/DocumentHistoryBlock.tsx`, чтобы:
 *  - чистая доменная логика жила в `domain/` (см. `react-frontend.mdc`, `testing.mdc`);
 *  - на неё собирался coverage (слой `domain/` входит в порог Vitest);
 *  - убрать дублирование лейблов статусов/событий с `documentLabels.ts`.
 */
import {
  DOCUMENT_ACTION_LABELS,
  DOCUMENT_STATUS_LABELS,
  TAG_IDS_REPLACED,
  TAG_IDS_REPLACED_LABEL,
} from './documentLabels'

const MAX_BODY_PREVIEW = 120

/** Лейблы полей, для которых есть человекочитаемое имя (остальные показываем как есть). */
export const DOCUMENT_HISTORY_FIELD_LABELS: Record<string, string> = {
  title: 'Заголовок',
  icon_emoji: 'Эмодзи',
  body: 'Текст',
  status: 'Статус',
  parent_document_id: 'Родительский документ',
  owner_sub: 'Владелец',
  tag_ids: 'Теги',
  action: 'Событие',
}

function truncateBody(s: string, max = MAX_BODY_PREVIEW): string {
  const t = s.replace(/\s+/g, ' ').trim()
  if (t.length <= max) return t
  return `${t.slice(0, max)}…`
}

/**
 * Извлекает текст из HTML-тела для превью в истории.
 * Использует `DOMParser` (не `innerHTML`), согласно `security.mdc` — это безопасный способ
 * извлечения textContent. HTML-комментарии не попадают в textContent, поэтому отдельно
 * не вырезаются. Fallback на regex — для окружений без `document` (ssr/тесты).
 */
export function bodyToPlainPreview(raw: string): string {
  if (typeof document !== 'undefined') {
    const parsed = new DOMParser().parseFromString(raw, 'text/html')
    const text = (parsed.body.textContent ?? '').replace(/\s+/g, ' ').trim()
    return text || '—'
  }
  return raw
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim() || '—'
}

function formatDocStatus(v: unknown): string {
  if (v === null || v === undefined) return '—'
  const s = String(v)
  return DOCUMENT_STATUS_LABELS[s] ?? s
}

function formatParentDocumentValue(v: unknown): string {
  if (v === null || v === undefined) return 'не задано'
  const s = String(v).trim()
  if (!s) return 'не задано'
  return 'задано'
}

function formatActionValue(v: unknown): string {
  if (v === null || v === undefined) return '—'
  const key = String(v)
  return DOCUMENT_ACTION_LABELS[key] ?? key
}

/** Форматирует значение поля истории для отображения. */
export function formatDocumentHistoryValue(
  field: string,
  v: unknown,
  resolveUserSub: (sub: string) => string,
): string {
  // parent_document_id: null/пусто → «не задано», иначе «задано» (информативнее «—»).
  if (field === 'parent_document_id') {
    return formatParentDocumentValue(v)
  }
  if (v === null || v === undefined) return '—'
  if (field === 'action') return formatActionValue(v)
  if (field === 'status') return formatDocStatus(v)
  if (field === 'owner_sub') {
    return typeof v === 'string' && v.length > 0 ? resolveUserSub(v) : '—'
  }
  if (field === 'tag_ids') {
    if (typeof v === 'string' && v === TAG_IDS_REPLACED) return TAG_IDS_REPLACED_LABEL
    return String(v)
  }
  if (field === 'body') {
    const str = typeof v === 'string' ? v : String(v)
    if (!str.trim()) return '—'
    return truncateBody(bodyToPlainPreview(str))
  }
  return typeof v === 'string' ? v : String(v)
}

/** true, если diff тегов — это сигнальный «заменён» (old=new=replaced). */
export function isTagIdsReplacedDiff(change: { old: unknown; new: unknown }): boolean {
  return (
    String(change.old) === TAG_IDS_REPLACED && String(change.new) === TAG_IDS_REPLACED
  )
}

/** true, если событие — создание документа (поле `action` со значением `created`). */
export function isDocumentCreatedAction(change: { old: unknown; new: unknown }): boolean {
  return String(change.new) === 'created'
}
