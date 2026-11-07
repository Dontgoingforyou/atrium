import { normalizeDocumentBody } from './normalizeDocumentBody'

/** Таймаут WS sync до fallback на локальный PATCH body. */
export const DOCUMENT_COLLAB_CONNECT_TIMEOUT_MS = 12_000

/** URL Hocuspocus collab (same-origin `/collab` за nginx). */
export function documentCollabWsUrl(): string {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}/collab`
}

export function documentCollabTicketPath(documentId: string): string {
  return `/portal/documents/${encodeURIComponent(documentId)}/collab-ws-ticket`
}

/** Persist через Hocuspocus только после успешного sync (не connecting/unavailable). */
export function isDocumentCollabPersistActive(
  status: 'idle' | 'connecting' | 'ready' | 'unavailable',
): boolean {
  return status === 'ready'
}

/** Цвет курсора из sub (стабильный hue). */
export function collabCaretColorFromSub(sub: string): string {
  let h = 0
  for (let i = 0; i < sub.length; i++) h = (h * 31 + sub.charCodeAt(i)) >>> 0
  const hue = h % 360
  return `hsl(${hue} 70% 45%)`
}

/** Тот же Y.Doc — не remount TipTap из-за новой ссылки на объект collaboration. */
export function isSameRichTextCollaboration(
  prev: { ydoc: unknown } | null | undefined,
  next: { ydoc: unknown } | null | undefined,
): boolean {
  if (!prev && !next) return true
  if (!prev || !next) return false
  return prev.ydoc === next.ydoc
}

/** Локальный черновик REST-редактора нужно залить в collab-editor после remount. */
export function shouldSeedCollabEditorFromLocalHtml(
  localHtml: string,
  collabEditorHtml: string,
): boolean {
  return normalizeDocumentBody(localHtml) !== normalizeDocumentBody(collabEditorHtml)
}
