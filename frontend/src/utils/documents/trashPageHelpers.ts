import type { PagedResponse } from '../../types/timeEntry'
import type { PortalDocumentTrashItem } from '../../types/document'

export type TrashPageData = PagedResponse<PortalDocumentTrashItem>

/** Целых суток до auto_purge_at (неотрицательное). */
export function daysUntil(iso: string): number {
  const end = new Date(iso).getTime()
  if (!Number.isFinite(end)) return 0
  const now = Date.now()
  return Math.max(0, Math.ceil((end - now) / (24 * 60 * 60 * 1000)))
}

/** Убрать строку из кэша списка корзины (optimistic undo). */
export function removeTrashItem(
  data: TrashPageData | undefined,
  id: string,
): TrashPageData | undefined {
  if (!data) return data
  const items = data.items.filter((row) => row.id !== id)
  if (items.length === data.items.length) return data
  return { ...data, items, total: Math.max(0, data.total - 1) }
}
