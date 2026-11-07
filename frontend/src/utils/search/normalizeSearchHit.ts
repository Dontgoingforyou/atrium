import type { SearchEntityType, SearchResult } from '../../types/search'
import { asRecord } from './_normalizeShared'

/** Преобразует один элемент ответа GET /portal/search (discriminator + вложенные объекты) в плоский SearchResult. */
export function normalizeSearchHit(raw: unknown): SearchResult {
  const r = asRecord(raw)
  if (!r) {
    throw new Error('Результат поиска: ожидался объект')
  }
  const entityType = r.entity_type as SearchEntityType | undefined
  switch (entityType) {
    case 'document': {
      const doc = asRecord(r.document)
      if (!doc) throw new Error('document: нет поля document')
      return {
        entity_type: 'document',
        entity_id: String(doc.id),
        title: doc.title != null ? String(doc.title) : null,
        snippet: null,
        created_at: doc.created_at != null ? String(doc.created_at) : null,
        nav_node_slug: doc.nav_node_slug != null ? String(doc.nav_node_slug) : null,
      }
    }
    case 'chat_message': {
      const chat = asRecord(r.chat)
      const message = asRecord(r.message)
      if (!chat || !message) throw new Error('chat_message: нет chat/message')
      const bodyExcerpt = message.body_excerpt != null ? String(message.body_excerpt) : ''
      return {
        entity_type: 'chat_message',
        entity_id: String(message.id),
        title: chat.title != null ? String(chat.title) : null,
        snippet: bodyExcerpt || null,
        created_at: message.created_at != null ? String(message.created_at) : null,
        nav_node_slug: null,
        chat: { id: String(chat.id), title: chat.title != null ? String(chat.title) : null },
        message: { id: String(message.id), body: bodyExcerpt },
      }
    }
    case 'task': {
      const task = asRecord(r.task)
      if (!task) throw new Error('task: нет поля task')
      return {
        entity_type: 'task',
        entity_id: String(task.id),
        title: task.title != null ? String(task.title) : null,
        snippet: task.description_excerpt != null ? String(task.description_excerpt) : null,
        created_at: task.created_at != null ? String(task.created_at) : null,
        nav_node_slug: null,
      }
    }
    case 'specialist': {
      const sp = asRecord(r.specialist)
      if (!sp) throw new Error('specialist: нет поля specialist')
      const name = sp.full_name != null ? String(sp.full_name) : null
      const email = sp.email != null ? String(sp.email) : null
      return {
        entity_type: 'specialist',
        entity_id: String(sp.sub),
        title: name ?? email ?? String(sp.sub),
        snippet: name && email ? email : null,
        created_at: null,
        nav_node_slug: null,
      }
    }
    case 'calendar_event': {
      const ev = asRecord(r.calendar_event)
      if (!ev) throw new Error('calendar_event: нет поля calendar_event')
      const calTitle = ev.calendar_title != null ? String(ev.calendar_title) : null
      const location = ev.location != null ? String(ev.location) : null
      const snippetParts = [calTitle, location].filter(Boolean)
      return {
        entity_type: 'calendar_event',
        entity_id: String(ev.id),
        title: ev.title != null ? String(ev.title) : null,
        snippet: snippetParts.length ? snippetParts.join(' · ') : null,
        created_at: ev.starts_at != null ? String(ev.starts_at) : null,
        nav_node_slug: null,
      }
    }
    default:
      throw new Error(`Неизвестный entity_type результата поиска: ${String(entityType)}`)
  }
}

export function normalizePortalSearchResults(raw: unknown): SearchResult[] {
  if (!Array.isArray(raw)) {
    return []
  }
  const out: SearchResult[] = []
  for (const item of raw) {
    try {
      out.push(normalizeSearchHit(item))
    } catch {
      /* пропускаем битые элементы — не ломаем весь поиск */
    }
  }
  return out
}
