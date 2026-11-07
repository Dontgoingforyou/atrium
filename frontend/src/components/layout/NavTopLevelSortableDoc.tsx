import { useDroppable } from '@dnd-kit/core'
import { useSortable } from '@dnd-kit/sortable'
import { CSS as DndKitCSS } from '@dnd-kit/utilities'
import { useParams } from 'react-router'
import type { ReactNode } from 'react'

import { navDocHasBranch } from '@/domain/documents/documentNavSections'
import type { NavDocBrief } from '../../types/portalNavigation'
import { NavDocumentShortcuts } from './NavDocumentShortcuts'
import { DraggablePortalNavTree } from './DraggablePortalNavTree'
import {
  NavDocActionsMenu,
  NavDocCollapseButton,
  NavDocLink,
} from './NavDocRowParts'
import { navDocBranchHidden, navDocNeedsCollapseSpace } from './navDocRowConstants'
import {
  NAV_DOC_LAYOUT_TRANSITION,
  docDndId,
  navDocAnimateLayoutChanges,
  sectionDndId,
} from './navDocumentDnd'
import styles from '@/styles/modules/layout/AppLayout.module.css'
import dndStyles from '@/styles/modules/layout/DraggablePortalNavTree.module.css'

/** Секция-приёмник верхнего уровня (Документы / Документы для разработчиков). */
export function DroppableSection({ slug, children }: { slug: string; children: ReactNode }) {
  const { setNodeRef, isOver } = useDroppable({ id: sectionDndId(slug) })
  return (
    <div
      ref={setNodeRef}
      className={`${styles.navDocumentSection}${isOver ? ` ${styles.navDocumentSectionDropOver}` : ''}`}
    >
      {children}
    </div>
  )
}

/** Перетаскиваемый документ верхнего уровня с вложенным DnD-деревом. */
export function TopLevelSortableDoc({
  doc,
  slug,
  sectionParentId,
  isBranchCollapsed,
  onToggleBranch,
  canEditDocuments,
  onNestedReorder,
}: {
  doc: NavDocBrief
  slug: string
  sectionParentId: string | null
  isBranchCollapsed: (id: string) => boolean
  onToggleBranch: (id: string) => void
  canEditDocuments: boolean
  onNestedReorder: (docId: string, body: { before_id?: string; after_id?: string }) => Promise<void>
}) {
  const { documentId: activeDocId } = useParams<{ documentId?: string }>()
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: docDndId(doc.id),
    animateLayoutChanges: navDocAnimateLayoutChanges,
  })
  const hasChildren = (doc.children?.length ?? 0) > 0
  const hasBranch = navDocHasBranch(doc)
  const hidden = navDocBranchHidden(doc, isBranchCollapsed)

  const style = {
    transform: DndKitCSS.Transform.toString(transform),
    transition: isDragging ? undefined : (transition ?? NAV_DOC_LAYOUT_TRANSITION),
    paddingLeft: 8,
  }

  return (
    <>
      <div
        ref={setNodeRef}
        style={style}
        data-nav-doc-id={doc.id}
        className={`${dndStyles.row} navDocRow ${activeDocId === doc.id ? dndStyles.rowActive : ''} ${isDragging ? dndStyles.itemDragging : ''}`}
        {...attributes}
      >
        <div className={dndStyles.dragHandle} {...listeners}>
          {hasBranch ? (
            <NavDocCollapseButton
              styles={dndStyles}
              hidden={hidden}
              onToggle={() => onToggleBranch(doc.id)}
              suppressDrag
            />
          ) : navDocNeedsCollapseSpace(0) ? (
            <span className={dndStyles.collapseSpace} aria-hidden />
          ) : null}
          <NavDocLink doc={doc} styles={dndStyles} suppressDrag />
        </div>
        <NavDocActionsMenu
          doc={doc}
          slug={slug}
          parentDocumentId={sectionParentId}
          canEditDocuments={canEditDocuments}
          suppressDrag
        />
      </div>

      {hasBranch ? (
        <div className={dndStyles.branchShell} data-state={hidden ? 'closed' : 'open'}>
          <div className={dndStyles.branchInner} inert={hidden || undefined}>
            {hasChildren ? (
              <DraggablePortalNavTree
                embedded
                documentsParentId={doc.id}
                onDocReorder={onNestedReorder}
                nodes={[
                  {
                    id: `child-of-${doc.id}`,
                    slug,
                    title: '',
                    sort_order: 0,
                    document_count_subtree: doc.children?.length ?? 0,
                    documents: doc.children ?? [],
                    children: [],
                  },
                ]}
                depth={1}
              />
            ) : null}
            <NavDocumentShortcuts
              shortcuts={doc.shortcuts ?? []}
              sourceDocumentId={doc.id}
              depth={1}
            />
          </div>
        </div>
      ) : null}
    </>
  )
}
