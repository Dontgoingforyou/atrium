type DocumentQuerySlice = {
  data?: { id: string; title?: string | null } | null
  isPending: boolean
  isFetching: boolean
}

export function resolveTaskLinkedDocumentTitle(
  documentId: string | null | undefined,
  documentQuery: DocumentQuerySlice,
  taskDocumentTitle?: string | null,
): { title: string; isLoading: boolean } {
  if (!documentId) {
    return { title: '', isLoading: false }
  }

  const queryMatches = documentQuery.data?.id === documentId
  const queryTitle = queryMatches ? documentQuery.data?.title?.trim() ?? '' : ''
  const embeddedTitle = taskDocumentTitle?.trim() ?? ''

  if (queryTitle) {
    return { title: queryTitle, isLoading: false }
  }

  if (embeddedTitle) {
    return {
      title: embeddedTitle,
      isLoading: documentQuery.isFetching && !queryMatches,
    }
  }

  if (documentQuery.isPending || (documentQuery.isFetching && !queryMatches)) {
    return { title: '', isLoading: true }
  }

  if (queryMatches) {
    return { title: `id ${documentId}`, isLoading: false }
  }

  return { title: `id ${documentId}`, isLoading: false }
}
