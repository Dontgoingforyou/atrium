import { PRIORITY_LABELS, STATUS_LABELS } from './taskUi'
import type { TaskPriority, TaskStatus } from '../../types/task'

const MAX_HISTORY_TEXT_PREVIEW = 120

function stripHtmlForHistory(text: string): string {
  if (!/[<>]/.test(text)) return text
  const doc = new DOMParser().parseFromString(text, 'text/html')
  const plain = doc.body.textContent?.trim() ?? ''
  return plain || text
}

export function truncateHistoryText(text: string, max = MAX_HISTORY_TEXT_PREVIEW): string {
  const t = text.replace(/\s+/g, ' ').trim()
  if (t.length <= max) return t
  return `${t.slice(0, max)}…`
}

function parseAssigneeSubsList(v: unknown): string[] {
  if (v === null || v === undefined) return []
  if (Array.isArray(v)) {
    return v.filter((x): x is string => typeof x === 'string' && x.length > 0)
  }
  if (typeof v === 'string') {
    const t = v.trim()
    if (!t) return []
    if (t.includes(',')) {
      return t
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean)
    }
    return [t]
  }
  return []
}

function formatAssigneeSubsHistory(
  v: unknown,
  resolveUserSub: (sub: string | null | undefined) => string,
): string {
  const subs = parseAssigneeSubsList(v)
  if (subs.length === 0) return '—'
  return subs.map((s) => resolveUserSub(s)).join(', ')
}

function formatDueAtHistoryValue(v: unknown): string {
  if (v === null || v === undefined) return '—'
  if (typeof v !== 'string') return String(v)
  const d = new Date(v)
  if (Number.isNaN(d.getTime())) return v
  return d.toLocaleDateString('ru-RU')
}

function idFromHistoryValue(v: unknown): string | null {
  if (v === null || v === undefined) return null
  if (typeof v === 'string' && v.length > 0) return v
  return null
}

export function formatHistoryValue(
  field: string,
  v: unknown,
  resolveUserSub: (sub: string | null | undefined) => string,
  resolvers: {
    documentTitle: (id: string) => string
    chatTitle: (id: string) => string
  },
): string {
  if (v === null || v === undefined) return '—'
  if (field === 'assignee_sub') {
    return typeof v === 'string' && v.length > 0 ? resolveUserSub(v) : '—'
  }
  if (field === 'assignee_subs') {
    return formatAssigneeSubsHistory(v, resolveUserSub)
  }
  if (field === 'description' && typeof v === 'string') {
    return truncateHistoryText(stripHtmlForHistory(v)) || '—'
  }
  if (field === 'status' && typeof v === 'string' && v in STATUS_LABELS) {
    return STATUS_LABELS[v as TaskStatus]
  }
  if (field === 'priority' && typeof v === 'string' && v in PRIORITY_LABELS) {
    return PRIORITY_LABELS[v as TaskPriority]
  }
  if (field === 'due_at') {
    return formatDueAtHistoryValue(v)
  }
  if (field === 'action' && typeof v === 'string') {
    if (v === 'created') return 'Создание задачи'
    return v
  }
  if (field === 'document_id') {
    const id = idFromHistoryValue(v)
    return id ? resolvers.documentTitle(id) : '—'
  }
  if (field === 'chat_id') {
    const id = idFromHistoryValue(v)
    return id ? resolvers.chatTitle(id) : '—'
  }
  return String(v)
}
