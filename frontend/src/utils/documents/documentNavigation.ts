import type { QueryClient } from '@tanstack/react-query'
import type { NavigateFunction } from 'react-router'

import { getDocument } from '../../api/documents/documentsApi'
import type { PortalDocument } from '../../types/document'
import { getDocumentPublicHref } from './documentHref'

export function normalizeDocumentId(id: string | undefined | null): string {
  return (id ?? '').trim().toLowerCase()
}

export function documentIdsMatch(a: string | undefined | null, b: string | undefined | null): boolean {
  return normalizeDocumentId(a) === normalizeDocumentId(b)
}

export const portalDocumentQueryKey = (documentId: string) =>
  ['portal', 'document', documentId] as const

/** Дочерние документы документа (используется из страницы документа, навигации, WS). */
export const documentChildrenQueryKey = (documentId: string) =>
  ['portal', 'document', documentId, 'children'] as const

/** Комментарии документа (страница документа + WS треда). */
export const documentCommentsQueryKey = (documentId: string) =>
  ['portal', 'document', documentId, 'comments'] as const

/** Вложения документа. */
export const documentFilesQueryKey = (documentId: string) =>
  ['portal', 'document', documentId, 'files'] as const

/** История изменений документа (drawer на странице документа). */
export const documentHistoryQueryKey = (documentId: string) =>
  ['portal', 'document', documentId, 'history'] as const

/** Недавние документы для диалога вставки ссылки на документ в rich-text. */
export const documentDialogRecentQueryKey = () => ['portal', 'documents', 'dialog-recent'] as const

/** Поиск документов для диалога вставки ссылки в rich-text. */
export const documentDialogSearchQueryKey = (query: string) =>
  ['portal', 'search', 'doc-link-dialog', query] as const

/** SPA-путь документа без slug раздела — делегирует в канон `getDocumentPublicHref`. */
export function portalDocumentHref(documentId: string): string {
  return getDocumentPublicHref(documentId)
}

export async function prefetchPortalDocument(
  qc: QueryClient,
  documentId: string,
): Promise<PortalDocument> {
  return qc.fetchQuery({
    queryKey: portalDocumentQueryKey(documentId),
    queryFn: () => getDocument(documentId),
    staleTime: 0,
  })
}

export async function navigateToPortalDocument(
  navigate: NavigateFunction,
  qc: QueryClient,
  documentId: string,
): Promise<void> {
  const href = portalDocumentHref(documentId)
  try {
    await prefetchPortalDocument(qc, documentId)
  } catch {
    qc.removeQueries({ queryKey: portalDocumentQueryKey(documentId), exact: true })
  }
  navigate(href)
}
