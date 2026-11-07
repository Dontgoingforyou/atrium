import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router'

import { deletePortalDocument, duplicatePortalDocument, patchPortalDocumentWithCas } from '../api/documents/documentsApi'
import { userFacingMessageFromUnknown } from '../utils/apiUserMessage'
import { invalidateDocumentTrash } from '../utils/documents/documentTrashQuery'
import { getDocumentPublicUrl } from '../utils/documents/documentHref'
import { documentChildrenQueryKey } from '../utils/documents/documentNavigation'
import { invalidatePortalSearchQueries } from '@/utils/search/invalidatePortalSearch'
import {
  patchNavigationTreeRemoveDocument,
  refetchPortalNavigationTree,
} from '@/utils/navigation/patchPortalNavigationTreeCache'
import {
  DEVELOPER_DOCS_ROOT_ID,
  NAV_SLUG_DEVELOPER_DOCS,
  NAV_SLUG_DOCUMENTS,
  isTopLevelForSectionMove,
} from '@/domain/documents/documentNavSections'

import { useDelayedActionContext } from './useDelayedActionContext'
import { useDocumentFavorite } from './useDocumentFavorite'
import { useNotifyToast } from './useNotifyToast'
import { useScheduleDeleteWithUndo } from './useScheduleDeleteWithUndo'

type Options = {
  documentId: string
  navNodeSlug?: string | null
  canEdit: boolean
  parentDocumentId?: string | null
  onToast?: (message: string) => void
  onDeleted?: () => void
  onDeleteRevert?: () => void
  onDuplicated?: (newDocumentId: string) => void
}

export function useDocumentActions({
  documentId,
  navNodeSlug,
  canEdit,
  parentDocumentId,
  onToast,
  onDeleted,
  onDeleteRevert,
  onDuplicated,
}: Options) {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const favorite = useDocumentFavorite(documentId)
  const scheduleDeleteWithUndo = useScheduleDeleteWithUndo()
  const notifyToast = useNotifyToast()
  const { hideOptimistically, showOptimistically, optimisticallyHiddenIds } = useDelayedActionContext()

  function toast(message: string) {
    onToast?.(message)
  }

  function alertError(error: unknown) {
    notifyToast(userFacingMessageFromUnknown(error))
  }

  const deleteMut = useMutation({
    mutationFn: () => deletePortalDocument(documentId),
    onSuccess: () => {
      invalidateDocumentTrash(qc)
      invalidatePortalSearchQueries(qc)
      refetchPortalNavigationTree(qc)
    },
    onError: alertError,
  })

  const duplicateMut = useMutation({
    mutationFn: () => duplicatePortalDocument(documentId),
    onSuccess: (result) => {
      toast('Копия документа создана')
      invalidatePortalSearchQueries(qc)
      refetchPortalNavigationTree(qc)
      onDuplicated?.(result.id)
      if (!onDuplicated) {
        void navigate(`/documents/${encodeURIComponent(result.id)}`)
      }
    },
    onError: alertError,
  })

  const moveSectionMut = useMutation({
    mutationFn: (parent_document_id: string | null) =>
      patchPortalDocumentWithCas(documentId, { parent_document_id }),
    onSuccess: () => {
      invalidatePortalSearchQueries(qc)
      refetchPortalNavigationTree(qc)
    },
    onError: alertError,
  })

  function handleDelete() {
    if (!canEdit || deleteMut.isPending) return
    // Дедуп в окне undo: повторный клик не плодит вторую delayed-операцию.
    if (optimisticallyHiddenIds.has(documentId)) return

    const childrenKey = parentDocumentId
      ? documentChildrenQueryKey(parentDocumentId)
      : null
    const previousChildren = childrenKey ? qc.getQueryData(childrenKey) : undefined

    scheduleDeleteWithUndo({
      message: 'Документ перемещён в корзину',
      optimistic: () => {
        hideOptimistically(documentId)
        patchNavigationTreeRemoveDocument(qc, documentId)
        if (childrenKey) {
          qc.setQueryData(childrenKey, (prev: unknown) => {
            if (!Array.isArray(prev)) return prev
            return prev.filter((d: { id: string }) => d.id !== documentId)
          })
        }
        onDeleted?.()
        if (!onDeleted) {
          const parentId = parentDocumentId
          void navigate(parentId ? `/documents/${encodeURIComponent(parentId)}` : '/')
        }
      },
      revert: () => {
        showOptimistically(documentId)
        refetchPortalNavigationTree(qc)
        if (childrenKey && previousChildren !== undefined) {
          qc.setQueryData(childrenKey, previousChildren)
        }
        onDeleteRevert?.()
      },
      onUndoClick: () => {
        showOptimistically(documentId)
      },
      commit: () => {
        deleteMut.mutate(undefined, {
          onSettled: () => {
            showOptimistically(documentId)
          },
        })
      },
    })
  }

  function handleDuplicate() {
    if (!canEdit || duplicateMut.isPending) return
    duplicateMut.mutate()
  }

  function handleMoveToDeveloperDocs() {
    if (!canEdit || moveSectionMut.isPending) return
    moveSectionMut.mutate(DEVELOPER_DOCS_ROOT_ID, {
      onSuccess: () => toast('Документ перенесён в «Документы для разработчиков»'),
    })
  }

  function handleMoveToGeneralDocs() {
    if (!canEdit || moveSectionMut.isPending) return
    moveSectionMut.mutate(null, {
      onSuccess: () => toast('Документ перенесён в «Документы»'),
    })
  }

  async function handleCopyLink() {
    try {
      await navigator.clipboard.writeText(getDocumentPublicUrl(documentId, navNodeSlug))
      toast('Ссылка скопирована')
    } catch {
      notifyToast('Не удалось скопировать ссылку')
    }
  }

  function handleToggleFavorite() {
    if (favorite.isPending) return
    favorite.toggleFavorite()
  }

  const canMoveBetweenSections = canEdit && isTopLevelForSectionMove(parentDocumentId)
  const canMoveToDeveloperDocs = canMoveBetweenSections && navNodeSlug === NAV_SLUG_DOCUMENTS
  const canMoveToGeneralDocs = canMoveBetweenSections && navNodeSlug === NAV_SLUG_DEVELOPER_DOCS

  return {
    canEdit,
    isFavorite: favorite.isFavorite,
    favoritePending: favorite.isPending,
    deletePending: deleteMut.isPending,
    duplicatePending: duplicateMut.isPending,
    moveSectionPending: moveSectionMut.isPending,
    canMoveToDeveloperDocs,
    canMoveToGeneralDocs,
    handleDelete,
    handleDuplicate,
    handleMoveToDeveloperDocs,
    handleMoveToGeneralDocs,
    handleCopyLink,
    handleToggleFavorite,
  }
}
