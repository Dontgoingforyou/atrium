import { useState } from 'react'
import { NavDocumentTreeIcon } from '../layout/NavDocumentTreeIcon'
import { FavoriteButton } from '../favorites/FavoriteButton'
import { DocumentActionsMenu } from './DocumentActionsMenu'
import type { PortalDocument } from '../../types/document'
import styles from '@/styles/modules/documents/PortalDocumentShell.module.css'

type Props = {
  documentId: string
  data: Pick<PortalDocument, 'id' | 'title' | 'icon_emoji' | 'parent_document_id' | 'nav_node_slug'>
  canEdit: boolean
  onSaveTitle: (title: string) => void
  onHistoryOpen: () => void
  onToast?: (message: string) => void
  onDeleted?: () => void
  onDeleteRevert?: () => void
}

export function DocumentTitleRow({
  documentId,
  data,
  canEdit,
  onSaveTitle,
  onHistoryOpen,
  onToast,
  onDeleted,
  onDeleteRevert,
}: Props) {
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState(data.title)

  function save() {
    const t = value.trim()
    if (!t || t === data.title) { setEditing(false); return }
    onSaveTitle(t)
    setEditing(false)
  }

  return (
    <div className={styles.titleRow} data-tour="document-title">
      <NavDocumentTreeIcon
        documentId={documentId}
        iconEmoji={data.icon_emoji}
        glyphClassName={styles.docPageIcon}
        size="page"
      />
      <div className={styles.titleGrow}>
        {canEdit && editing ? (
          <input
            className={styles.titleInput}
            value={value}
            autoFocus
            maxLength={512}
            aria-label="Заголовок документа"
            onChange={(e) => setValue(e.target.value)}
            onBlur={save}
            onKeyDown={(e) => {
              if (e.key === 'Enter') { e.preventDefault(); save() }
              if (e.key === 'Escape') { setValue(data.title); setEditing(false) }
            }}
          />
        ) : (
          <h1
            className={`${styles.title} ${canEdit ? styles.titleEditable : ''}`}
            title={canEdit ? 'Нажмите, чтобы изменить заголовок' : undefined}
            onClick={() => {
              if (!canEdit) return
              setValue(data.title)
              setEditing(true)
            }}
          >
            {data.title}
          </h1>
        )}
      </div>

      <div className={styles.titleActions}>
        <FavoriteButton documentId={data.id} title={data.title} />
        <DocumentActionsMenu
          documentId={data.id}
          title={data.title}
          navNodeSlug={data.nav_node_slug}
          canEdit={canEdit}
          parentDocumentId={data.parent_document_id}
          variant="inline"
          onToast={onToast}
          onDeleted={onDeleted}
          onDeleteRevert={onDeleteRevert}
          onHistoryOpen={canEdit ? onHistoryOpen : undefined}
        />
      </div>
    </div>
  )
}
