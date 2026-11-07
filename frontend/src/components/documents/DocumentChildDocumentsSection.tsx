import { useNavigate } from 'react-router'
import {
  DndContext,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import {
  SortableContext,
  arrayMove,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useRef } from 'react'

import { listChildDocuments, quickCreateDocument, reorderPortalDocument } from '../../api/documents/documentsApi'
import { SortableChildDocRow } from './SortableChildDocRow'
import { IconDocRowPlus } from '../icons/portalIcons'
import { UNTITLED_DOCUMENT_LABEL } from '@/domain/documents/documentLabels'
import { useDelayedActionContext } from '../../hooks/useDelayedActionContext'
import { useNotifyToast } from '../../hooks/useNotifyToast'
import type { PortalDocument, PortalDocumentBrief } from '../../types/document'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { playUiSound } from '../../utils/sound/uiSounds'
import { navigateToPortalDocument, documentChildrenQueryKey } from '../../utils/documents/documentNavigation'
import { resolveDocumentReorderAnchor } from '../../utils/documents/resolveDocumentReorderAnchor'
import { invalidatePortalSearchQueries } from '@/utils/search/invalidatePortalSearch'
import {
  patchNavigationTreeAppendChildDocument,
  patchNavigationTreeReorderChildrenOfParent,
  refetchPortalNavigationTree,
} from '@/utils/navigation/patchPortalNavigationTreeCache'
import aside from '@/styles/modules/documents/PortalDocumentAside.module.css'

type Props = {
  documentId: string
  data: PortalDocument
  canEditDocuments: boolean
  currentUserSub: string
}

/** Список дочерних документов и кнопка быстрого создания. */
export function DocumentChildDocumentsSection({
  documentId,
  data,
  canEditDocuments,
  currentUserSub,
}: Props) {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const notifyToast = useNotifyToast()
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }))
  /** После DnD тачпад часто шлёт click — не открывать документ (как в канбане). */
  const suppressNavAfterDragRef = useRef<string | null>(null)

  const { data: childDocs, isPending: childrenLoading, isError: childrenError, error: childrenErr } = useQuery({
    queryKey: documentChildrenQueryKey(documentId),
    queryFn: () => listChildDocuments(documentId),
  })
  const { optimisticallyHiddenIds } = useDelayedActionContext()
  const visibleChildDocs = useMemo(() => {
    if (!childDocs) return undefined
    if (optimisticallyHiddenIds.size === 0) return childDocs
    return childDocs.filter((d) => !optimisticallyHiddenIds.has(d.id))
  }, [childDocs, optimisticallyHiddenIds])

  const sortableIds = useMemo(
    () => (visibleChildDocs ?? []).map((d) => d.id),
    [visibleChildDocs],
  )

  const reorderMut = useMutation({
    mutationFn: (payload: {
      documentId: string
      body: { before_id?: string; after_id?: string }
      previous: PortalDocumentBrief[]
    }) => reorderPortalDocument(payload.documentId, payload.body),
    onError: (e, vars) => {
      qc.setQueryData(documentChildrenQueryKey(documentId), vars.previous)
      refetchPortalNavigationTree(qc)
      notifyToast(userFacingMessageFromUnknown(e))
    },
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: documentChildrenQueryKey(documentId) })
      refetchPortalNavigationTree(qc)
    },
  })

  const quickCreateSubMut = useMutation({
    mutationFn: () => quickCreateDocument({ parent_document_id: documentId }),
    onSuccess: async (result) => {
      playUiSound('success')
      const now = new Date().toISOString()
      const childBrief: PortalDocumentBrief = {
        id: result.id,
        title: UNTITLED_DOCUMENT_LABEL,
        icon_emoji: null,
        parent_document_id: documentId,
        author_sub: currentUserSub,
        created_at: now,
        updated_at: now,
      }
      qc.setQueryData<PortalDocumentBrief[]>(documentChildrenQueryKey(documentId), (old) => {
        if (old?.some((d) => d.id === result.id)) return old
        const siblings = old ?? []
        return [childBrief, ...siblings]
      })
      patchNavigationTreeAppendChildDocument(qc, documentId, {
        id: result.id,
        title: UNTITLED_DOCUMENT_LABEL,
        icon_emoji: null,
        children: [],
      })
      // Документ уже создан на сервере — кэши инвалидируем независимо от того,
      // удалось ли сразу перейти на новую страницу (иначе при ошибке навигации
      // дети/дерево/поиск останутся рассинхронизированы с сервером).
      queueMicrotask(() => {
        void qc.invalidateQueries({ queryKey: documentChildrenQueryKey(documentId) })
        refetchPortalNavigationTree(qc)
        invalidatePortalSearchQueries(qc)
      })
      try {
        await navigateToPortalDocument(navigate, qc, result.id)
      } catch (e) {
        notifyToast(userFacingMessageFromUnknown(e), {
          silent: true,
          actionLabel: 'Открыть',
          onAction: () => void navigateToPortalDocument(navigate, qc, result.id),
        })
      }
    },
    onError: (e) => notifyToast(userFacingMessageFromUnknown(e), { tone: 'error' }),
  })

  function handleDragEnd(event: DragEndEvent) {
    const movedId = String(event.active.id)
    suppressNavAfterDragRef.current = movedId
    window.setTimeout(() => {
      if (suppressNavAfterDragRef.current === movedId) {
        suppressNavAfterDragRef.current = null
      }
    }, 400)

    const { active, over } = event
    if (!over || active.id === over.id || !visibleChildDocs) return
    const oldIndex = visibleChildDocs.findIndex((d) => d.id === active.id)
    const newIndex = visibleChildDocs.findIndex((d) => d.id === over.id)
    if (oldIndex < 0 || newIndex < 0) return

    const previous = visibleChildDocs
    const next = arrayMove(visibleChildDocs, oldIndex, newIndex)
    const anchor = resolveDocumentReorderAnchor(next, movedId)
    if (!anchor) return

    qc.setQueryData(documentChildrenQueryKey(documentId), next)
    patchNavigationTreeReorderChildrenOfParent(
      qc,
      documentId,
      next.map((d) => d.id),
    )
    reorderMut.mutate({ documentId: movedId, body: anchor, previous })
  }

  const enableDnd =
    canEditDocuments && !childrenLoading && (visibleChildDocs?.length ?? 0) > 1

  const showBlock =
    childrenLoading || (visibleChildDocs?.length ?? 0) > 0 || canEditDocuments

  if (!showBlock) return null

  const list =
    childrenError ? (
      <p className="text-danger" role="alert">{userFacingMessageFromUnknown(childrenErr)}</p>
    ) : childrenLoading ? (
      <p className={aside.subDocsLoading}>Загрузка…</p>
    ) : (
      (visibleChildDocs ?? []).map((doc) => (
        <SortableChildDocRow
          key={doc.id}
          doc={doc}
          parentDocumentId={documentId}
          navNodeSlug={data.nav_node_slug}
          canEdit={canEditDocuments}
          sortable={enableDnd}
          suppressNavAfterDragRef={suppressNavAfterDragRef}
          onToast={notifyToast}
        />
      ))
    )

  return (
    <div className={aside.subDocsList}>
      {enableDnd ? (
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <SortableContext items={sortableIds} strategy={verticalListSortingStrategy}>
            {list}
          </SortableContext>
        </DndContext>
      ) : (
        list
      )}
      {canEditDocuments ? (
        <button
          type="button"
          className={aside.addDocBtn}
          disabled={quickCreateSubMut.isPending}
          onClick={() => quickCreateSubMut.mutate()}
        >
          <span className={aside.docLeadIcon} aria-hidden>
            <IconDocRowPlus />
          </span>
          {quickCreateSubMut.isPending ? 'Создание…' : 'Новый документ'}
        </button>
      ) : null}
    </div>
  )
}
