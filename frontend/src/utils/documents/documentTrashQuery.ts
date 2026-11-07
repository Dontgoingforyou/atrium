import type { QueryClient } from '@tanstack/react-query'

export const DOCUMENT_TRASH_QUERY_KEY = ['portal', 'document-trash'] as const

export function invalidateDocumentTrash(qc: QueryClient): void {
  void qc.invalidateQueries({ queryKey: DOCUMENT_TRASH_QUERY_KEY })
  void qc.refetchQueries({ queryKey: DOCUMENT_TRASH_QUERY_KEY })
}
