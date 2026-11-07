import { useState } from 'react'
import type { Editor } from '@tiptap/react'
import type { ReactNode } from 'react'
import {
  TextB,
  TextItalic,
  TextUnderline,
  ListBullets,
  ListNumbers,
  ListChecks,
  TextIndent,
  TextOutdent,
  TextT,
  Link as LinkIcon,
  FileText,
} from '@phosphor-icons/react'
import styles from '@/styles/modules/tasks/RichTextEditorToolbar.module.css'
import {
  FONT_FAMILY_OPTIONS,
  FONT_SIZE_OPTIONS,
  LINE_HEIGHT_OPTIONS,
  PARAGRAPH_STYLE_OPTIONS,
} from './constants'
import { applyFontFamily } from './useRichTextEditor'
import { ImageInsertMenu } from './toolbar/ImageInsertMenu'
import { LinkDialog } from './toolbar/LinkDialog'
import { DocumentLinkDialog } from './toolbar/DocumentLinkDialog'
import { AlignMenu } from './toolbar/AlignMenu'
import { MoreMenu } from './toolbar/MoreMenu'
import { ColorPickers } from './toolbar/ColorPickers'
import { toggleExclusiveList } from './richTextListCommands'

type Props = {
  editor: Editor | null
  entityType?: 'task' | 'document'
  entityId?: string
  uploadImages?: (files: File[]) => void | Promise<void>
  linkOpen: boolean
  onLinkOpenChange: (open: boolean) => void
  /** Режим sheet (страница документа) — модификаторы тулбара. */
  appearance?: 'default' | 'sheet'
  /** Внешний sticky-слот тулбара документа. */
  toolbarExternal?: boolean
}

function currentParagraphStyle(editor: Editor | null): string {
  if (!editor) return 'paragraph'
  if (editor.isActive('heading', { level: 1 })) return 'h1'
  if (editor.isActive('heading', { level: 2 })) return 'h2'
  if (editor.isActive('heading', { level: 3 })) return 'h3'
  return 'paragraph'
}

function applyParagraphStyle(editor: Editor, value: string) {
  const chain = editor.chain().focus().unsetFontSize()
  if (value === 'paragraph') {
    chain.setParagraph().run()
    return
  }
  const level = Number(value.replace('h', '')) as 1 | 2 | 3
  chain.setHeading({ level }).run()
}

function stepFontSize(editor: Editor, delta: number) {
  const current =
    (editor.getAttributes('textStyle').fontSize as string | undefined) || '12px'
  const idx = FONT_SIZE_OPTIONS.findIndex((o) => o.value === current)
  const baseIdx = idx >= 0 ? idx : FONT_SIZE_OPTIONS.findIndex((o) => o.value === '12px')
  const next = Math.max(0, Math.min(FONT_SIZE_OPTIONS.length - 1, baseIdx + delta))
  const nextVal = FONT_SIZE_OPTIONS[next]?.value
  if (nextVal) editor.chain().focus().setFontSize(nextVal).run()
}

function ToolbarBtn({
  title,
  active,
  disabled,
  onAction,
  children,
}: {
  title: string
  active?: boolean
  disabled?: boolean
  onAction: () => void
  children: ReactNode
}) {
  return (
    <button
      type="button"
      tabIndex={-1}
      title={title}
      aria-label={title}
      disabled={disabled}
      className={`${styles.toolbarBtn} ${active ? styles.toolbarBtnActive : ''}`}
      onMouseDown={(e) => {
        e.preventDefault()
        onAction()
      }}
    >
      {children}
    </button>
  )
}

export function RichTextToolbar({
  editor,
  entityType,
  entityId,
  uploadImages,
  linkOpen,
  onLinkOpenChange,
  appearance = 'default',
  toolbarExternal = false,
}: Props) {
  const [docLinkOpen, setDocLinkOpen] = useState(false)
  const fontSize = (editor?.getAttributes('textStyle').fontSize as string | undefined) || '12px'
  const fontFamily = (editor?.getAttributes('textStyle').fontFamily as string | undefined) || ''

  return (
    <div
      className={[
        styles.toolbar,
        appearance === 'sheet' ? styles.toolbarInSheet : '',
        appearance === 'sheet' && toolbarExternal ? styles.toolbarInSheetExternal : '',
      ].filter(Boolean).join(' ')}
      role="toolbar" aria-label="Панель форматирования" aria-orientation="horizontal">
      <select
        className={styles.toolbarSelect}
        title="Структура: заголовок для оглавления и поиска; размер шрифта — только внешний вид"
        aria-label="Стиль абзаца"
        value={currentParagraphStyle(editor)}
        onMouseDown={(e) => e.stopPropagation()}
        onChange={(e) => editor && applyParagraphStyle(editor, e.target.value)}
      >
        {PARAGRAPH_STYLE_OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>

      <select
        className={styles.toolbarSelect}
        title="Шрифт"
        aria-label="Шрифт"
        value={fontFamily}
        onMouseDown={(e) => e.stopPropagation()}
        onChange={(e) => editor && applyFontFamily(editor, e.target.value)}
      >
        {FONT_FAMILY_OPTIONS.map((o) => (
          <option key={o.label} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>

      <div className={styles.fontSizeStepper}>
        <button
          type="button"
          tabIndex={-1}
          className={styles.stepperBtn}
          title="Уменьшить размер"
          onMouseDown={(e) => {
            e.preventDefault()
            if (editor) stepFontSize(editor, -1)
          }}
        >
          −
        </button>
        <span className={styles.fontSizeValue}>{fontSize.replace('px', '')}</span>
        <button
          type="button"
          tabIndex={-1}
          className={styles.stepperBtn}
          title="Увеличить размер"
          onMouseDown={(e) => {
            e.preventDefault()
            if (editor) stepFontSize(editor, 1)
          }}
        >
          +
        </button>
      </div>

      <div className={styles.toolbarDivider} />

      <ToolbarBtn title="Жирный (Ctrl+B)" active={editor?.isActive('bold')} onAction={() => editor?.chain().focus().toggleBold().run()}>
        <TextB size={16} weight="bold" aria-hidden />
      </ToolbarBtn>
      <ToolbarBtn title="Курсив (Ctrl+I)" active={editor?.isActive('italic')} onAction={() => editor?.chain().focus().toggleItalic().run()}>
        <TextItalic size={16} aria-hidden />
      </ToolbarBtn>
      <ToolbarBtn title="Подчёркнутый (Ctrl+U)" active={editor?.isActive('underline')} onAction={() => editor?.chain().focus().toggleUnderline().run()}>
        <TextUnderline size={16} aria-hidden />
      </ToolbarBtn>

      <ColorPickers editor={editor} />

      <div className={styles.toolbarDivider} />

      <ToolbarBtn
        title="Ссылка на выделенный текст (Ctrl+K)"
        active={editor?.isActive('link')}
        onAction={() => onLinkOpenChange(true)}
      >
        <LinkIcon size={16} aria-hidden />
      </ToolbarBtn>
      <LinkDialog
        open={linkOpen}
        initialUrl={(editor?.getAttributes('link').href as string) ?? ''}
        onClose={() => onLinkOpenChange(false)}
        onApply={(url) => {
          editor?.chain().focus().extendMarkRange('link').setLink({ href: url }).run()
        }}
        onRemove={() => {
          editor?.chain().focus().extendMarkRange('link').unsetLink().run()
        }}
      />

      <ToolbarBtn
        title="Вставить ссылку на документ портала"
        onAction={() => setDocLinkOpen(true)}
      >
        <FileText size={16} aria-hidden />
      </ToolbarBtn>
      <DocumentLinkDialog
        open={docLinkOpen}
        onClose={() => setDocLinkOpen(false)}
        onInsert={(doc) => {
          editor?.chain().focus().insertDocumentLink({ documentId: doc.id, documentTitle: doc.title }).run()
        }}
      />

      <ImageInsertMenu
        editor={editor}
        entityType={entityType}
        entityId={entityId}
        uploadImages={uploadImages}
      />

      <div className={styles.toolbarDivider} />

      <AlignMenu editor={editor} />

      <select
        className={styles.toolbarSelectNarrow}
        title="Межстрочный интервал"
        aria-label="Межстрочный интервал"
        value={(editor?.getAttributes('paragraph').lineHeight as string) || (editor?.getAttributes('heading').lineHeight as string) || '1.5'}
        onMouseDown={(e) => e.stopPropagation()}
        onChange={(e) => {
          const v = e.target.value
          if (v) editor?.chain().focus().setLineHeight(v).run()
        }}
      >
        {LINE_HEIGHT_OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>

      <div className={styles.toolbarDivider} />

      <ToolbarBtn
        title="Чеклист"
        active={editor?.isActive('taskList')}
        onAction={() => editor && toggleExclusiveList(editor, 'taskList')}
      >
        <ListChecks size={16} aria-hidden />
      </ToolbarBtn>
      <ToolbarBtn
        title="Маркированный список"
        active={editor?.isActive('bulletList')}
        onAction={() => editor && toggleExclusiveList(editor, 'bulletList')}
      >
        <ListBullets size={16} aria-hidden />
      </ToolbarBtn>
      <ToolbarBtn
        title="Нумерованный список"
        active={editor?.isActive('orderedList')}
        onAction={() => editor && toggleExclusiveList(editor, 'orderedList')}
      >
        <ListNumbers size={16} aria-hidden />
      </ToolbarBtn>
      <ToolbarBtn
        title="Уменьшить отступ"
        onAction={() => editor?.chain().focus().outdentParagraph().run()}
      >
        <TextOutdent size={16} aria-hidden />
      </ToolbarBtn>
      <ToolbarBtn
        title="Увеличить отступ"
        onAction={() => editor?.chain().focus().indentParagraph().run()}
      >
        <TextIndent size={16} aria-hidden />
      </ToolbarBtn>
      <ToolbarBtn
        title="Очистить форматирование"
        onAction={() =>
          editor?.chain().focus().clearNodes().unsetAllMarks().run()
        }
      >
        <TextT size={16} aria-hidden />
      </ToolbarBtn>

      <div className={styles.toolbarDivider} />

      <MoreMenu editor={editor} />
    </div>
  )
}
