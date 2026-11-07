import { Link } from 'react-router'

import { DEVELOPER_DOCS_ROOT_ID, DEVELOPER_DOCS_TITLE, GENERAL_DOCS_TITLE } from '@/domain/documents/documentNavSections'
import { UNTITLED_DOCUMENT_LABEL } from '@/domain/documents/documentLabels'
import type { PortalDocument } from '../../types/document'
import styles from '@/styles/modules/documents/PortalDocumentShell.module.css'

type BreadcrumbItem = PortalDocument['breadcrumb'][number]

type Props = {
  breadcrumb: BreadcrumbItem[]
  currentTitle: string
  embedded?: boolean
}

export function DocumentBreadcrumbNav({ breadcrumb, currentTitle, embedded = false }: Props) {
  const title = currentTitle.trim() || UNTITLED_DOCUMENT_LABEL
  const inDeveloperDocs = breadcrumb.some((b) => b.id === DEVELOPER_DOCS_ROOT_ID)
  const ancestors = inDeveloperDocs
    ? breadcrumb.filter((b) => b.id !== DEVELOPER_DOCS_ROOT_ID)
    : breadcrumb
  const rootLabel = inDeveloperDocs ? DEVELOPER_DOCS_TITLE : GENERAL_DOCS_TITLE

  const barClass = embedded
    ? `${styles.breadcrumbBar} ${styles.breadcrumbBarEmbedded}`
    : styles.breadcrumbBar

  return (
    <nav className={barClass} aria-label="Навигация по документам">
      <ol className={styles.breadcrumbList}>
        <li className={styles.breadcrumbItem}>
          {inDeveloperDocs ? (
            <span className={styles.breadcrumbLink}>{rootLabel}</span>
          ) : (
            <Link to="/" className={styles.breadcrumbLink}>
              {rootLabel}
            </Link>
          )}
        </li>
        {ancestors.map((b) => (
          <li key={b.id} className={styles.breadcrumbItem}>
            <span className={styles.breadcrumbSep} aria-hidden>
              /
            </span>
            <Link to={`/documents/${encodeURIComponent(b.id)}`} className={styles.breadcrumbLink}>
              {b.title.trim() || UNTITLED_DOCUMENT_LABEL}
            </Link>
          </li>
        ))}
        <li className={styles.breadcrumbItem}>
          <span className={styles.breadcrumbSep} aria-hidden>
            /
          </span>
          <span className={styles.breadcrumbCurrent} aria-current="page">
            {title}
          </span>
        </li>
      </ol>
    </nav>
  )
}
