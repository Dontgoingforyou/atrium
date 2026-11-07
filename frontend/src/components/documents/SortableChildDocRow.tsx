import { Link } from 'react-router'
import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import type { CSSProperties, MutableRefObject, ReactNode } from 'react'

import { DocumentActionsMenu } from './DocumentActionsMenu'
import { UNTITLED_DOCUMENT_LABEL } from '@/domain/documents/documentLabels'
import type { PortalDocumentBrief } from '../../types/document'
import aside from '@/styles/modules/documents/PortalDocumentAside.module.css'

type Props = {
  doc: PortalDocumentBrief
  parentDocumentId: string
  navNodeSlug: string | null
  canEdit: boolean
  sortable: boolean
  suppressNavAfterDragRef?: MutableRefObject<string | null>
  onToast?: (message: string) => void
}

function SubDocIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden>
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

function ChildDocRowShell({
  doc,
  parentDocumentId,
  navNodeSlug,
  canEdit,
  onToast,
  rowClass,
  style,
  dragAreaProps,
  setNodeRef,
  suppressNavAfterDragRef,
  isDragging,
}: {
  doc: PortalDocumentBrief
  parentDocumentId: string
  navNodeSlug: string | null
  canEdit: boolean
  onToast?: (message: string) => void
  rowClass: string
  style?: CSSProperties
  dragAreaProps?: Record<string, unknown>
  setNodeRef?: (node: HTMLElement | null) => void
  suppressNavAfterDragRef?: MutableRefObject<string | null>
  isDragging?: boolean
}) {
  const docUrl = `/documents/${encodeURIComponent(doc.id)}`
  return (
    <div ref={setNodeRef} style={style} className={rowClass}>
      <div className={aside.subDocDragArea} {...dragAreaProps}>
        <Link
          to={docUrl}
          className={aside.subDocLink}
          style={{ pointerEvents: isDragging ? 'none' : undefined }}
          onClick={(e) => {
            e.stopPropagation()
            if (suppressNavAfterDragRef?.current === doc.id) {
              e.preventDefault()
              suppressNavAfterDragRef.current = null
            }
          }}
        >
          {doc.icon_emoji ? (
            <span className={`${aside.docLeadIcon} ${aside.subDocEmoji}`} aria-hidden>
              {doc.icon_emoji}
            </span>
          ) : (
            <span className={`${aside.docLeadIcon} ${aside.docLeadIconMuted}`} aria-hidden>
              <SubDocIcon />
            </span>
          )}
          <span className={aside.subDocTitle}>{doc.title.trim() || UNTITLED_DOCUMENT_LABEL}</span>
          <span className={aside.subDocChevron} aria-hidden>
            ›
          </span>
        </Link>
      </div>
      <div
        className={aside.subDocMenu}
        onClick={(event) => event.stopPropagation()}
        onPointerDown={(event) => event.stopPropagation()}
      >
        <DocumentActionsMenu
          documentId={doc.id}
          title={doc.title}
          navNodeSlug={navNodeSlug}
          canEdit={canEdit}
          parentDocumentId={parentDocumentId}
          variant="inline"
          onToast={onToast}
        />
      </div>
    </div>
  )
}

function SortableChildDocRowInner(props: Omit<Props, 'sortable'>) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: props.doc.id,
  })
  const style: CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
  }
  const rowClass = [
    aside.subDocRow,
    aside.subDocRowSortable,
    isDragging ? aside.subDocRowDragging : '',
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <ChildDocRowShell
      {...props}
      rowClass={rowClass}
      style={style}
      setNodeRef={setNodeRef}
      dragAreaProps={{ ...attributes, ...listeners }}
      isDragging={isDragging}
    />
  )
}

export function SortableChildDocRow({ sortable, ...rest }: Props): ReactNode {
  if (!sortable) {
    return <ChildDocRowShell {...rest} rowClass={aside.subDocRow} />
  }
  return <SortableChildDocRowInner {...rest} />
}
