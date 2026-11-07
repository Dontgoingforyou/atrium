import type { SearchEntityType, SearchResult } from '../../types/search'
import { asRecord } from './_normalizeShared'

function metaStr(meta: Record<string, unknown>, key: string): string | null {
  const v = meta[key]
  return v != null && v !== '' ? String(v) : null
}

function excerptTitle(textExcerpt: string, maxLen = 120): string {
  const t = textExcerpt.trim()
  if (!t) return ''
  const line = t.split('\n')[0]?.trim() ?? t
  return line.length > maxLen ? `${line.slice(0, maxLen - 1)}…` : line
}

/** Элемент ответа GET /portal/search/semantic → плоский SearchResult для UI. */
export function normalizeSemanticHit(raw: unknown): SearchResult {
  const r = asRecord(raw)
  if (!r) {
    throw new Error('Семантический результат: ожидался объект')
  }
  const entityType = r.entity_type as SearchEntityType | undefined
  const entityId = r.entity_id != null ? String(r.entity_id) : ''
  const textExcerpt = r.text_excerpt != null ? String(r.text_excerpt) : ''
  const rawScore = r.similarity_score
  const similarity = typeof rawScore === 'number' && Number.isFinite(rawScore) ? rawScore : null
  const meta = asRecord(r.meta) ?? {}

  const base = {
    entity_id: entityId,
    snippet: textExcerpt || null,
    created_at: null,
    nav_node_slug: null,
    similarity_score: similarity,
  }

  switch (entityType) {
    case 'document':
      return {
        ...base,
        entity_type: 'document',
        title: excerptTitle(textExcerpt) || entityId,
      }
    case 'chat_message': {
      const chatId = metaStr(meta, 'chat_id')
      return {
        ...base,
        entity_type: 'chat_message',
        title: null,
        chat: chatId ? { id: chatId, title: null } : null,
        message: { id: entityId, body: textExcerpt },
      }
    }
    case 'task':
      return {
        ...base,
        entity_type: 'task',
        title: excerptTitle(textExcerpt) || entityId,
      }
    case 'agreement':
      return {
        ...base,
        entity_type: 'agreement',
        title: excerptTitle(textExcerpt) || entityId,
      }
    case 'learning_material':
      return {
        ...base,
        entity_type: 'learning_material',
        title: excerptTitle(textExcerpt) || entityId,
      }
    case 'specialist': {
      const sub = metaStr(meta, 'specialist_sub') ?? entityId
      return {
        ...base,
        entity_type: 'specialist',
        entity_id: sub,
        title: excerptTitle(textExcerpt) || sub,
      }
    }
    case 'specialist_note': {
      const specialistSub = metaStr(meta, 'specialist_sub')
      return {
        ...base,
        entity_type: 'specialist_note',
        entity_id: entityId,
        title: excerptTitle(textExcerpt) || 'Заметка о специалисте',
        specialist_sub: specialistSub,
      }
    }
    case 'calendar_event':
      return {
        ...base,
        entity_type: 'calendar_event',
        title: excerptTitle(textExcerpt) || entityId,
      }
    default:
      throw new Error(`Неизвестный entity_type семантического поиска: ${String(entityType)}`)
  }
}

export function normalizePortalSemanticResults(raw: unknown): SearchResult[] {
  const root = asRecord(raw)
  const list = root?.results
  if (!Array.isArray(list)) {
    return []
  }
  const out: SearchResult[] = []
  for (const item of list) {
    try {
      out.push(normalizeSemanticHit(item))
    } catch {
      /* пропускаем битые элементы — не ломаем весь поиск */
    }
  }
  return out
}
