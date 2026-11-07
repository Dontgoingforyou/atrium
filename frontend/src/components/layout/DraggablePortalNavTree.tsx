import {
  DndContext,
  DragOverlay,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import { SortableContext, arrayMove, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useParams } from 'react-router'

import { reorderPortalDocument } from '../../api/documents/documentsApi'
import { PORTAL_NAVIGATION_TREE_QUERY_KEY } from '../../api/queryKeys'
import { documentChildrenQueryKey } from '../../utils/documents/documentNavigation'
import { resolveDocumentReorderAnchor } from '../../utils/documents/resolveDocumentReorderAnchor'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { useNavTreeBranchCollapse } from '../../hooks/useNavTreeBranchCollapse'
import { useNotifyToast } from '../../hooks/useNotifyToast'
import { useAuthStore } from '../../store/authStore'
import { isUserManagerOrAdmin } from '@/domain/auth/authRoles'
import { navDocHasBranch } from '@/domain/documents/documentNavSections'
import type { NavDocBrief, PortalNavNodeTree } from '../../types/portalNavigation'
import { NavDocumentShortcuts } from './NavDocumentShortcuts'
import {
  NAV_DOC_DROP_ANIMATION,
  NAV_DOC_LAYOUT_TRANSITION,
  docDndId,
  navDocAnimateLayoutChanges,
  parseDocDndId,
} from './navDocumentDnd'
import {
  DocGlyph,
  NavDocActionsMenu,
  NavDocCollapseButton,
  NavDocLink,
} from './NavDocRowParts'
import { navDocBranchHidden, navDocIndentStyle, navDocNeedsCollapseSpace } from './navDocRowConstants'
import styles from '@/styles/modules/layout/DraggablePortalNavTree.module.css'

type Props = {
  nodes: PortalNavNodeTree[]
  depth?: number
  embedded?: boolean
  documentsParentId?: string | null
  onDocReorder?: DocReorderFn
}

type DocReorderFn = (docId: string, body: { before_id?: string; after_id?: string }) => Promise<void>

/* ─────────── Контейнер nav-узла (только оборачивает, без drag) ─────────── */
function NavGroupContainer({ children }: { children?: React.ReactNode }) {
  return <li className={styles.item}>{children}</li>
}

/* ─────────── Рекурсивный уровень nav-узлов ─────────── */
type NavLevelProps = {
  nodes: PortalNavNodeTree[]
  depth: number
  documentsParentId: string | null
  embedded: boolean
  onDocReorder: DocReorderFn
  isBranchCollapsed: (id: string) => boolean
  onToggleBranch: (id: string) => void
  canEditDocuments: boolean
}

function NavLevel({
  nodes,
  depth,
  documentsParentId,
  embedded,
  onDocReorder,
  isBranchCollapsed,
  onToggleBranch,
  canEditDocuments,
}: NavLevelProps) {
  return (
    <ul className={styles.list}>
      {nodes.map((n) => (
        <NavGroupContainer key={n.id}>
          <SortableDocBranch
            docs={n.documents ?? []}
            slug={n.slug}
            depth={depth}
            parentDocumentId={documentsParentId}
            embedded={embedded}
            onDocReorder={onDocReorder}
            isBranchCollapsed={isBranchCollapsed}
            onToggleBranch={onToggleBranch}
            canEditDocuments={canEditDocuments}
          />
          {n.children.length > 0 ? (
            <NavLevel
              nodes={n.children}
              depth={depth + 1}
              documentsParentId={documentsParentId}
              embedded={embedded}
              onDocReorder={onDocReorder}
              isBranchCollapsed={isBranchCollapsed}
              onToggleBranch={onToggleBranch}
              canEditDocuments={canEditDocuments}
            />
          ) : null}
        </NavGroupContainer>
      ))}
    </ul>
  )
}

/* ─────────── Список документов: DnD только если не embedded ─────────── */
function SortableDocBranch({
  docs,
  slug,
  depth,
  parentDocumentId,
  embedded,
  onDocReorder,
  isBranchCollapsed,
  onToggleBranch,
  canEditDocuments,
}: {
  docs: NavDocBrief[]
  slug: string
  depth: number
  parentDocumentId: string | null
  embedded: boolean
  onDocReorder: DocReorderFn
  isBranchCollapsed: (id: string) => boolean
  onToggleBranch: (id: string) => void
  canEditDocuments: boolean
}) {
  /** Локальный порядок только для собственного DndContext; в embedded — источник правды у родителя. */
  const [localDocs, setLocalDocs] = useState(docs)
  const [prevDocs, setPrevDocs] = useState(docs)
  const [activeDocId, setActiveDocId] = useState<string | null>(null)
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }))

  if (!embedded && docs !== prevDocs) {
    setPrevDocs(docs)
    const sameOrder = docs.length === localDocs.length && docs.every((d, i) => d.id === localDocs[i]?.id)
    if (!sameOrder) {
      setLocalDocs(docs)
    } else {
      const byId = new Map(docs.map((d) => [d.id, d]))
      setLocalDocs(localDocs.map((ld) => byId.get(ld.id) ?? ld))
    }
  }

  const displayDocs = embedded ? docs : localDocs
  const ids = displayDocs.map((d) => docDndId(d.id))
  const activeDoc = activeDocId ? (displayDocs.find((d) => d.id === activeDocId) ?? null) : null

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event
    setActiveDocId(null)
    if (!over || active.id === over.id) return

    const movedId = parseDocDndId(active.id)
    const overId = parseDocDndId(over.id)
    if (!movedId || !overId) return
    const activeIndex = displayDocs.findIndex((d) => d.id === movedId)
    const overIndex = displayDocs.findIndex((d) => d.id === overId)
    if (activeIndex < 0 || overIndex < 0) return

    const newOrder = arrayMove(displayDocs, activeIndex, overIndex)
    setLocalDocs(newOrder)

    const body = resolveDocumentReorderAnchor(newOrder, movedId)
    if (!body) return

    void onDocReorder(movedId, body)
  }

  if (!displayDocs.length) return null

  const list = (
    <SortableContext items={ids} strategy={verticalListSortingStrategy}>
      {displayDocs.map((doc) => (
        <SortableDocItem
          key={doc.id}
          doc={doc}
          slug={slug}
          depth={depth}
          parentDocumentId={parentDocumentId}
          embedded={embedded}
          onDocReorder={onDocReorder}
          isBranchCollapsed={isBranchCollapsed}
          onToggleBranch={onToggleBranch}
          canEditDocuments={canEditDocuments}
        />
      ))}
    </SortableContext>
  )

  if (embedded) {
    return list
  }

  return (
    <DndContext
      sensors={sensors}
      autoScroll
      collisionDetection={closestCenter}
      onDragStart={({ active }) => {
        const id = parseDocDndId(active.id)
        if (id) setActiveDocId(id)
      }}
      onDragEnd={handleDragEnd}
      onDragCancel={() => setActiveDocId(null)}
    >
      {list}
      <DragOverlay dropAnimation={NAV_DOC_DROP_ANIMATION}>
        {activeDoc ? (
          <div className={styles.overlay}>
            <DocGlyph className={styles.overlayIcon} />
            <span>{activeDoc.title}</span>
          </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  )
}

/* ─────────── Перетаскиваемый элемент-документ ─────────── */
function SortableDocItem({
  doc,
  slug,
  depth,
  parentDocumentId,
  embedded,
  isBranchCollapsed,
  onToggleBranch,
  onDocReorder,
  canEditDocuments,
}: {
  doc: NavDocBrief
  slug: string
  depth: number
  parentDocumentId: string | null
  embedded: boolean
  onDocReorder: DocReorderFn
  isBranchCollapsed: (id: string) => boolean
  onToggleBranch: (id: string) => void
  canEditDocuments: boolean
}) {
  const { documentId: activeDocId } = useParams<{ documentId?: string }>()
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: docDndId(doc.id),
    animateLayoutChanges: navDocAnimateLayoutChanges,
  })
  const hasChildren = (doc.children?.length ?? 0) > 0
  const hasBranch = navDocHasBranch(doc)
  const hidden = navDocBranchHidden(doc, isBranchCollapsed)
  void embedded
  void onDocReorder

  const style = {
    transform: CSS.Transform.toString(transform),
    transition: isDragging ? undefined : (transition ?? NAV_DOC_LAYOUT_TRANSITION),
    ...navDocIndentStyle(depth),
  }

  const rowClass = [
    styles.row,
    'navDocRow',
    activeDocId === doc.id ? styles.rowActive : '',
    isDragging ? styles.itemDragging : '',
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <>
      <div
        ref={setNodeRef}
        style={style}
        data-nav-doc-id={doc.id}
        className={rowClass}
        {...attributes}
      >
        <div className={styles.dragHandle} {...listeners}>
          {hasBranch ? (
            <NavDocCollapseButton
              styles={styles}
              hidden={hidden}
              onToggle={() => onToggleBranch(doc.id)}
              suppressDrag
            />
          ) : navDocNeedsCollapseSpace(depth) ? (
            <span className={styles.collapseSpace} aria-hidden />
          ) : null}
          <NavDocLink doc={doc} styles={styles} suppressDrag />
        </div>
        <NavDocActionsMenu
          doc={doc}
          slug={slug}
          parentDocumentId={parentDocumentId}
          canEditDocuments={canEditDocuments}
          suppressDrag
        />
      </div>

      {hasBranch ? (
        <div className={styles.branchShell} data-state={hidden ? 'closed' : 'open'}>
          <div className={styles.branchInner} inert={hidden || undefined}>
            {hasChildren ? (
              <SortableDocBranch
                docs={doc.children ?? []}
                slug={slug}
                depth={depth + 1}
                parentDocumentId={doc.id}
                embedded={embedded}
                onDocReorder={onDocReorder}
                isBranchCollapsed={isBranchCollapsed}
                onToggleBranch={onToggleBranch}
                canEditDocuments={canEditDocuments}
              />
            ) : null}
            <NavDocumentShortcuts
              shortcuts={doc.shortcuts ?? []}
              sourceDocumentId={doc.id}
              depth={depth + 1}
            />
          </div>
        </div>
      ) : null}
    </>
  )
}

export function DraggablePortalNavTree({
  nodes,
  depth = 0,
  embedded = false,
  documentsParentId = null,
  onDocReorder: onDocReorderProp,
}: Props) {
  const qc = useQueryClient()
  const notify = useNotifyToast()
  const { isCollapsed, toggle: toggleBranch } = useNavTreeBranchCollapse()
  const user = useAuthStore((s) => s.user)
  const canEditDocuments = Boolean(user && isUserManagerOrAdmin(user))

  const reorderDocMutation = useMutation({
    mutationFn: async (payload: { documentId: string; body: { before_id?: string; after_id?: string } }) =>
      reorderPortalDocument(payload.documentId, payload.body),
    onError: (e) => {
      notify(userFacingMessageFromUnknown(e))
    },
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: PORTAL_NAVIGATION_TREE_QUERY_KEY })
      if (documentsParentId) {
        void qc.invalidateQueries({
          queryKey: documentChildrenQueryKey(documentsParentId),
        })
      }
    },
  })

  async function handleDocReorder(docId: string, body: { before_id?: string; after_id?: string }) {
    if (onDocReorderProp) {
      await onDocReorderProp(docId, body)
      return
    }
    reorderDocMutation.mutate({ documentId: docId, body })
  }

  return (
    <NavLevel
      nodes={nodes}
      depth={depth}
      documentsParentId={documentsParentId}
      embedded={embedded}
      onDocReorder={handleDocReorder}
      isBranchCollapsed={isCollapsed}
      onToggleBranch={toggleBranch}
      canEditDocuments={canEditDocuments}
    />
  )
}
