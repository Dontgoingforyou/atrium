import { useAuthStore } from '../../store/authStore'
import { useNavTreeBranchCollapse } from '../../hooks/useNavTreeBranchCollapse'
import { isUserManagerOrAdmin } from '@/domain/auth/authRoles'
import { navDocHasBranch } from '@/domain/documents/documentNavSections'
import type { NavDocBrief, PortalNavNodeTree } from '../../types/portalNavigation'
import { NavDocumentShortcuts } from './NavDocumentShortcuts'
import {
  NavDocActionsMenu,
  NavDocCollapseButton,
  NavDocLink,
} from './NavDocRowParts'
import { navDocBranchHidden, navDocIndentStyle, navDocNeedsCollapseSpace } from './navDocRowConstants'
import styles from '@/styles/modules/layout/PortalNavTree.module.css'

type NavTreeProps = {
  nodes: PortalNavNodeTree[]
  depth: number
  documentsParentId: string | null
  isBranchCollapsed: (id: string) => boolean
  onToggleBranch: (id: string) => void
  canEditDocuments: boolean
}

function NavTreeList({
  nodes,
  depth,
  documentsParentId,
  isBranchCollapsed,
  onToggleBranch,
  canEditDocuments,
}: NavTreeProps) {
  const items: React.ReactNode[] = []

  for (const n of nodes) {
    for (const doc of n.documents ?? []) {
      items.push(
        <DocItem
          key={doc.id}
          doc={doc}
          slug={n.slug}
          depth={depth}
          parentDocumentId={documentsParentId}
          isBranchCollapsed={isBranchCollapsed}
          onToggleBranch={onToggleBranch}
          canEditDocuments={canEditDocuments}
        />,
      )
    }
    if (n.children.length > 0) {
      items.push(
        <NavTreeList
          key={`nav-${n.id}`}
          nodes={n.children}
          depth={depth + 1}
          documentsParentId={documentsParentId}
          isBranchCollapsed={isBranchCollapsed}
          onToggleBranch={onToggleBranch}
          canEditDocuments={canEditDocuments}
        />,
      )
    }
  }

  if (items.length === 0) return null
  return <ul className={depth ? styles.listNested : styles.list}>{items}</ul>
}

function DocItem({
  doc,
  slug,
  depth,
  parentDocumentId,
  isBranchCollapsed,
  onToggleBranch,
  canEditDocuments,
}: {
  doc: NavDocBrief
  slug: string
  depth: number
  parentDocumentId: string | null
  isBranchCollapsed: (id: string) => boolean
  onToggleBranch: (id: string) => void
  canEditDocuments: boolean
}) {
  const hasBranch = navDocHasBranch(doc)
  const hidden = navDocBranchHidden(doc, isBranchCollapsed)
  const shortcuts = doc.shortcuts ?? []
  const children = doc.children ?? []

  return (
    <li className={styles.item}>
      <div className={`${styles.row} navDocRow`} style={navDocIndentStyle(depth)}>
        {hasBranch ? (
          <NavDocCollapseButton
            styles={styles}
            hidden={hidden}
            onToggle={() => onToggleBranch(doc.id)}
          />
        ) : navDocNeedsCollapseSpace(depth) ? (
          <span className={styles.collapseSpace} aria-hidden />
        ) : null}
        <NavDocLink doc={doc} styles={styles} />
        <NavDocActionsMenu
          doc={doc}
          slug={slug}
          parentDocumentId={parentDocumentId}
          canEditDocuments={canEditDocuments}
        />
      </div>

      {hasBranch ? (
        <div className={styles.branchShell} data-state={hidden ? 'closed' : 'open'}>
          <div className={styles.branchInner} inert={hidden || undefined}>
            {children.length > 0 ? (
              <ul className={styles.listNested}>
                {children.map((child) => (
                  <DocItem
                    key={child.id}
                    doc={child}
                    slug={slug}
                    depth={depth + 1}
                    parentDocumentId={doc.id}
                    isBranchCollapsed={isBranchCollapsed}
                    onToggleBranch={onToggleBranch}
                    canEditDocuments={canEditDocuments}
                  />
                ))}
              </ul>
            ) : null}
            <NavDocumentShortcuts
              shortcuts={shortcuts}
              sourceDocumentId={doc.id}
              depth={depth + 1}
            />
          </div>
        </div>
      ) : null}
    </li>
  )
}

export function PortalNavTree({
  nodes,
  documentsParentId = null,
}: {
  nodes: PortalNavNodeTree[]
  documentsParentId?: string | null
}) {
  const { isCollapsed, toggle } = useNavTreeBranchCollapse()
  const user = useAuthStore((s) => s.user)
  const canEditDocuments = Boolean(user && isUserManagerOrAdmin(user))

  return (
    <NavTreeList
      nodes={nodes}
      depth={0}
      documentsParentId={documentsParentId}
      isBranchCollapsed={isCollapsed}
      onToggleBranch={toggle}
      canEditDocuments={canEditDocuments}
    />
  )
}
