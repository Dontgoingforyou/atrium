/** Нормализация HTML-тела документа перед сравнением и сохранением. */
export function normalizeDocumentBody(html: string | null | undefined): string | null {
  if (html == null) return null
  const trimmed = html.trim()
  return trimmed || null
}

export function documentBodyIsDirty(draft: string, saved: string | null | undefined): boolean {
  return normalizeDocumentBody(draft) !== normalizeDocumentBody(saved ?? '')
}
