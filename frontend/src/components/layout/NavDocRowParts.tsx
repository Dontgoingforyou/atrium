import { Link, useNavigate, useParams } from 'react-router'
import { useRef } from 'react'

import { DocumentActionsMenu } from '../documents/DocumentActionsMenu'
import { NavDocumentTreeIcon } from './NavDocumentTreeIcon'
import type { NavDocBrief } from '../../types/portalNavigation'

type NavStyles = Record<string, string>

/** SVG-глиф документа (одна копия на каталог). */
export function DocGlyph({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M7 3h7l5 5v11a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path d="M14 3v5h5" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M9.5 13.5h5M9.5 16.5h5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  )
}

/** Кнопка свернуть/развернуть ветку документа (с a11y: aria-expanded + aria-label). */
export function NavDocCollapseButton({
  styles,
  hidden,
  onToggle,
  suppressDrag,
}: {
  styles: NavStyles
  hidden: boolean
  onToggle: () => void
  /** В DnD-режиме клик/pointerdown на кнопке не должен инициировать перетаскивание. */
  suppressDrag?: boolean
}) {
  return (
    <button
      type="button"
      className={styles.collapseBtn}
      title={hidden ? 'Развернуть' : 'Свернуть'}
      aria-label={hidden ? 'Развернуть ветку документа' : 'Свернуть ветку документа'}
      aria-expanded={!hidden}
      onPointerDown={suppressDrag ? (e) => e.stopPropagation() : undefined}
      onClick={(e) => {
        if (suppressDrag) e.stopPropagation()
        onToggle()
      }}
    >
      <span className={styles.collapseIcon} data-state={hidden ? 'closed' : 'open'} aria-hidden>
        ▾
      </span>
    </button>
  )
}

/** Ссылка на документ в навигации (иконка + название), с подсветкой активного. */
export function NavDocLink({
  doc,
  styles,
  suppressDrag,
}: {
  doc: NavDocBrief
  styles: NavStyles
  /** В DnD-режиме клик не должен инициировать перетаскивание. */
  suppressDrag?: boolean
}) {
  const { documentId: activeDocId } = useParams<{ documentId?: string }>()
  const to = `/documents/${encodeURIComponent(doc.id)}`
  return (
    <Link
      to={to}
      className={`${styles.link} ${activeDocId === doc.id ? styles.linkActive : ''}`}
      onClick={suppressDrag ? (e) => e.stopPropagation() : undefined}
    >
      <NavDocumentTreeIcon documentId={doc.id} iconEmoji={doc.icon_emoji} glyphClassName={styles.pageIcon} />
      <span className={styles.linkText}>{doc.title}</span>
    </Link>
  )
}

/**
 * Меню действий документа в навигации + обработка удаления активного документа:
 * при удалении активного — уход на '/', при undo — возврат обратно.
 * Раньше onDeleted/onDeleteRevert дублировались в 3 местах каталога.
 */
export function NavDocActionsMenu({
  doc,
  slug,
  parentDocumentId,
  canEditDocuments,
  suppressDrag,
}: {
  doc: NavDocBrief
  slug: string
  parentDocumentId: string | null
  canEditDocuments: boolean
  suppressDrag?: boolean
}) {
  const navigate = useNavigate()
  const { documentId: activeDocId } = useParams<{ documentId?: string }>()
  const navigatedOnDeleteRef = useRef(false)
  return (
    <DocumentActionsMenu
      documentId={doc.id}
      title={doc.title}
      navNodeSlug={slug}
      parentDocumentId={parentDocumentId}
      canEdit={canEditDocuments}
      variant="nav"
      onPointerDownMenu={suppressDrag ? (e) => e.stopPropagation() : undefined}
      onDeleted={() => {
        if (activeDocId === doc.id) {
          navigatedOnDeleteRef.current = true
          void navigate('/')
        }
      }}
      onDeleteRevert={() => {
        if (navigatedOnDeleteRef.current) {
          navigatedOnDeleteRef.current = false
          void navigate(`/documents/${encodeURIComponent(doc.id)}`)
        }
      }}
    />
  )
}
