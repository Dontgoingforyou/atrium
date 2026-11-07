import { Link, useParams } from 'react-router'

import type { NavDocBrief } from '../../types/portalNavigation'
import { NavDocumentTreeIcon } from './NavDocumentTreeIcon'
import { navDocIndentStyle } from './navDocRowConstants'
import styles from '@/styles/modules/layout/PortalNavTree.module.css'

type Props = {
  shortcuts: NavDocBrief[]
  sourceDocumentId: string
  depth: number
}

/** Ярлыки documentLink — только навигация, без DnD и меню действий. */
export function NavDocumentShortcuts({ shortcuts, sourceDocumentId, depth }: Props) {
  const { documentId: activeDocId } = useParams<{ documentId?: string }>()
  if (shortcuts.length === 0) return null

  return (
    <ul className={styles.listNested}>
      {shortcuts.map((sc) => {
        const to = `/documents/${encodeURIComponent(sc.id)}`
        return (
          <li key={`shortcut-${sourceDocumentId}-${sc.id}`} className={styles.item}>
            <div
              className={`${styles.row} ${styles.shortcutRow}`}
              style={navDocIndentStyle(depth)}
            >
              <span className={styles.collapseSpace} aria-hidden />
              <Link
                to={to}
                className={`${styles.link} ${styles.shortcutLink} ${activeDocId === sc.id ? styles.linkActive : ''}`}
                title="Ярлык на документ"
              >
                <NavDocumentTreeIcon
                  documentId={sc.id}
                  iconEmoji={sc.icon_emoji}
                  glyphClassName={styles.pageIcon}
                />
                <span className={styles.linkText}>{sc.title}</span>
              </Link>
            </div>
          </li>
        )
      })}
    </ul>
  )
}
