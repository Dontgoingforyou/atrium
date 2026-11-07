import { useMemo } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router'

import { quickCreateDocument } from '../../api/documents/documentsApi'
import { PORTAL_NAVIGATION_TREE_QUERY_KEY } from '../../api/queryKeys'
import { useDelayedActionContext } from '../../hooks/useDelayedActionContext'
import { useNotifyToast } from '../../hooks/useNotifyToast'
import { parentDocumentIdForNavSlug } from '@/domain/documents/documentNavSections'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { playUiSound } from '../../utils/sound/uiSounds'
import { filterNavTreeHiddenDocuments } from '@/utils/navigation/patchPortalNavigationTreeCache'
import type { PortalNavNodeTree } from '../../types/portalNavigation'
import { PortalNavTree } from './PortalNavTree'
import { CrossSectionDraggableNav } from './CrossSectionDraggableNav'
import styles from '@/styles/modules/layout/AppLayout.module.css'

type Props = {
  navTree: PortalNavNodeTree[]
  navLoading: boolean
  navError: boolean
  onRetry: () => void
  canEdit: boolean
  useDraggable: boolean
}

/**
 * Секции левого меню документов по ответу navigation-tree
 * (ДОКУМЕНТЫ + ДОКУМЕНТЫ ДЛЯ РАЗРАБОТЧИКОВ).
 */
export function PortalDocumentsNavSections({
  navTree,
  navLoading,
  navError,
  onRetry,
  canEdit,
  useDraggable,
}: Props) {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const notify = useNotifyToast()
  const { optimisticallyHiddenIds } = useDelayedActionContext()

  const visibleNavTree = useMemo(
    () => filterNavTreeHiddenDocuments(navTree, optimisticallyHiddenIds),
    [navTree, optimisticallyHiddenIds],
  )

  const createMut = useMutation({
    mutationFn: (slug: string) =>
      quickCreateDocument({
        parent_document_id: parentDocumentIdForNavSlug(slug),
      }),
    onSuccess: (result) => {
      playUiSound('success')
      void qc.invalidateQueries({ queryKey: PORTAL_NAVIGATION_TREE_QUERY_KEY })
      void navigate(`/documents/${encodeURIComponent(result.id)}`)
    },
    onError: (e) => notify(userFacingMessageFromUnknown(e), { tone: 'error' }),
  })

  if (navLoading) {
    return <span className={styles.navLoading}>Загрузка меню…</span>
  }
  if (navError) {
    return (
      <span className={styles.navError}>
        Меню недоступно.{' '}
        <button type="button" className={styles.navRetryBtn} onClick={onRetry}>
          Повторить
        </button>
      </span>
    )
  }
  if (!visibleNavTree.length) {
    return canEdit ? (
      <p className={styles.navEmpty} data-tour="nav-documents">
        Документов нет. Нажмите +, чтобы создать первый.
      </p>
    ) : null
  }

  if (!useDraggable) {
    return (
      <div className={styles.navDocumentsScroll} data-tour="nav-documents">
        <div className={styles.navDocumentsInner}>
          {visibleNavTree.map((section) => (
            <div key={section.id} className={styles.navDocumentSection}>
              <div className={styles.sectionHeader}>
                <span className={styles.sectionLabel}>{section.title.toUpperCase()}</span>
              </div>
              {(section.documents?.length ?? 0) > 0 ? (
                <PortalNavTree
                  nodes={[section]}
                  documentsParentId={parentDocumentIdForNavSlug(section.slug)}
                />
              ) : (
                <p className={styles.navEmpty}>Пока нет документов.</p>
              )}
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div data-tour="nav-documents">
      <CrossSectionDraggableNav
        navTree={visibleNavTree}
        canEdit={canEdit}
        onCreate={(slug) => createMut.mutate(slug)}
        createPending={createMut.isPending}
      />
    </div>
  )
}
