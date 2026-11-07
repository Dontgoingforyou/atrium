import { useLayoutEffect, useMemo } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'

import { getDocument } from '../../api/documents/documentsApi'
import { useAuthStore } from '../../store/authStore'
import { usePortalUserDirectory } from '../../hooks/usePortalUserDirectory'
import { isTimesheetOnlyUser, isUserManagerOrAdmin } from '@/domain/auth/authRoles'
import {
  documentIdsMatch,
  portalDocumentQueryKey,
} from '../../utils/documents/documentNavigation'
import type { PortalDocument } from '../../types/document'

export type PortalDocumentPageData = {
  canEditDocuments: boolean
  currentUserSub: string
  isPortalAdmin: boolean
  loadPortalUsers: boolean
  resolveUserSub: (s: string) => string
  avatarBySub: Record<string, string | undefined>
  document: PortalDocument | undefined
  isPending: boolean
  isError: boolean
  error: unknown
  isFetching: boolean
  reloadDocument: () => void
}

/**
 * Запросы и производные флаги страницы документа (без UI-оркестрации редактирования).
 * См. react-frontend.mdc: оркестрация выносится в колоцированный хук рядом со страницей.
 */
export function usePortalDocumentPageData(documentId: string): PortalDocumentPageData {
  const qc = useQueryClient()
  const user = useAuthStore((s) => s.user)
  const canEditDocuments = Boolean(user && isUserManagerOrAdmin(user))
  const timesheetOnly = Boolean(user && isTimesheetOnlyUser(user))
  const currentUserSub = user?.sub ?? ''
  const isPortalAdmin = Boolean(user?.is_portal_admin)
  const loadPortalUsers = !timesheetOnly

  const usersDirectory = usePortalUserDirectory({
    // Timesheet-only не имеют доступа к /portal/users — имя автора приходит в комментарии.
    enabled: Boolean(user) && !timesheetOnly,
  })
  const resolveUserSub = usersDirectory.getLabel
  const avatarBySub = useMemo(() => {
    const m: Record<string, string | undefined> = {}
    for (const u of usersDirectory.users) {
      m[u.sub] = u.avatar_url ?? undefined
    }
    return m
  }, [usersDirectory.users])

  const { data, isPending, isError, error, isFetching } = useQuery({
    queryKey: portalDocumentQueryKey(documentId),
    queryFn: () => getDocument(documentId),
    staleTime: 0,
    refetchOnMount: 'always',
  })

  // Сброс закэшированного документа, если ключ почему-то держит данные с другим id
  // (защита от рассинхрона ключа и payload после навигации).
  useLayoutEffect(() => {
    const cached = qc.getQueryData<PortalDocument>(portalDocumentQueryKey(documentId))
    if (cached && !documentIdsMatch(cached.id, documentId)) {
      qc.removeQueries({ queryKey: portalDocumentQueryKey(documentId), exact: true })
    }
  }, [documentId, qc])

  const document = data && documentIdsMatch(data.id, documentId) ? data : undefined

  const reloadDocument = () => {
    void qc.invalidateQueries({ queryKey: portalDocumentQueryKey(documentId) })
  }

  return {
    canEditDocuments,
    currentUserSub,
    isPortalAdmin,
    loadPortalUsers,
    resolveUserSub,
    avatarBySub,
    document,
    isPending,
    isError,
    error,
    isFetching,
    reloadDocument,
  }
}
