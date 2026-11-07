import { createPortal } from 'react-dom'
import type { CSSProperties } from 'react'
import { useState } from 'react'
import { EditorContent } from '@tiptap/react'
import styles from '@/styles/modules/tasks/RichTextEditor.module.css'
import contentStyles from '@/styles/modules/tasks/RichTextEditorContent.module.css'
import { useRichTextEditor, type RichTextCollaboration } from './useRichTextEditor'
import { RichTextToolbar } from './RichTextToolbar'
import { RichTextEditorDropZone } from './RichTextEditorDropZone'
import { TableFloatingMenu } from './toolbar/TableFloatingMenu'

export type RichTextEntityType = 'task' | 'document'

export interface RichTextEditorProps {
  content: string
  onChange: (html: string) => void
  placeholder?: string
  minRows?: number
  ariaLabelledBy?: string
  /** Для загрузки изображений с диска (нужен сохранённый id сущности). */
  entityType?: RichTextEntityType
  entityId?: string
  /** Без рамки вокруг редактора — «пустой лист» (страница документа). */
  appearance?: 'default' | 'sheet'
  /** Панель форматирования; по умолчанию true. */
  showToolbar?: boolean
  /** Анимация панели в режиме sheet (страница документа). */
  toolbarExpanded?: boolean
  /** Внешний слот для тулбара (sticky chrome документа); без собственного sticky. */
  toolbarSlotEl?: HTMLElement | null
  /** Режим ввода; false — просмотр с той же вёрсткой TipTap. */
  editable?: boolean
  /** Фокус в редактор при монтировании; для задач — false (фокус на названии). */
  autoFocus?: boolean
  /** Yjs collab (только document body). */
  collaboration?: RichTextCollaboration | null
}

export function RichTextEditor({
  content,
  onChange,
  minRows = 3,
  ariaLabelledBy,
  entityType,
  entityId,
  appearance = 'default',
  showToolbar = true,
  toolbarExpanded = true,
  toolbarSlotEl,
  editable = true,
  autoFocus = true,
  collaboration = null,
}: RichTextEditorProps) {
  const sheetToolbar = appearance === 'sheet' && showToolbar
  const externalToolbar = sheetToolbar && toolbarSlotEl != null
  const [, setFormatTick] = useState(0)
  const [linkOpen, setLinkOpen] = useState(false)
  const { editor, uploadImages } = useRichTextEditor({
    content,
    onChange,
    editable,
    autoFocus,
    entityType,
    entityId,
    collaboration,
    onFormatTick: () => setFormatTick((n) => n + 1),
    onLinkShortcut: () => setLinkOpen(true),
  })

  const wrapperClass = [
    styles.wrapper,
    appearance === 'sheet' ? styles.wrapperSheet : '',
    appearance === 'sheet' && !editable ? styles.wrapperSheetIdle : '',
  ]
    .filter(Boolean)
    .join(' ')

  const toolbarNode = (
    <RichTextToolbar
      editor={editor}
      entityType={entityType}
      entityId={entityId}
      uploadImages={uploadImages}
      linkOpen={linkOpen}
      onLinkOpenChange={setLinkOpen}
      appearance={appearance}
      toolbarExternal={externalToolbar}
    />
  )

  const toolbarWrapClass = [
    styles.toolbarSheetWrap,
    toolbarExpanded ? styles.toolbarSheetWrapOpen : '',
    externalToolbar ? styles.toolbarSheetWrapExternal : '',
  ]
    .filter(Boolean)
    .join(' ')

  const renderToolbar = () => {
    if (!sheetToolbar) {
      return showToolbar ? toolbarNode : null
    }
    const wrap = (
      <div className={toolbarWrapClass} data-rich-text-toolbar-root>
        <div className={styles.toolbarSheetInner}>{toolbarNode}</div>
      </div>
    )
    if (externalToolbar) {
      if (!toolbarSlotEl) return null
      return createPortal(wrap, toolbarSlotEl)
    }
    return wrap
  }

  return (
    <div className={wrapperClass} aria-labelledby={ariaLabelledBy || undefined}>
      {renderToolbar()}
      {editor && editable ? <TableFloatingMenu editor={editor} /> : null}
      <RichTextEditorDropZone
        editor={editor}
        entityType={entityType}
        entityId={entityId}
        uploadImages={uploadImages}
      >
        <EditorContent
          editor={editor}
          className={[
            styles.editor,
            contentStyles.editor,
            appearance === 'sheet' ? styles.editorInSheet : '',
            appearance === 'sheet' && !editable ? styles.editorInSheetIdle : '',
          ]
            .filter(Boolean)
            .join(' ')}
          style={{ '--min-rows': minRows } as CSSProperties}
        />
      </RichTextEditorDropZone>
    </div>
  )
}
