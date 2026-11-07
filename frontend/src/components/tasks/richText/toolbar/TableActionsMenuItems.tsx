import type { Editor } from '@tiptap/react'
import {
  ArrowLeft,
  ArrowRight,
  ColumnsPlusLeft,
  RowsPlusTop,
  Trash,
} from '@phosphor-icons/react'
import styles from '@/styles/modules/tasks/RichTextEditorToolbar.module.css'

type Props = {
  editor: Editor
  onDone?: () => void
}

/** Пункты меню операций над таблицей (общий источник для floating ⋯). */
export function TableActionsMenuItems({ editor, onDone }: Props) {
  return (
    <>
      <button
        type="button"
        role="menuitem"
        className={styles.dropdownItem}
        disabled={!editor.can().addRowAfter()}
        onMouseDown={(e) => e.preventDefault()}
        onClick={() => editor.chain().focus().addRowAfter().run()}
      >
        <RowsPlusTop size={18} aria-hidden />
        <span>Добавить строку</span>
      </button>
      <button
        type="button"
        role="menuitem"
        className={styles.dropdownItem}
        disabled={!editor.can().addColumnAfter()}
        onMouseDown={(e) => e.preventDefault()}
        onClick={() => editor.chain().focus().addColumnAfter().run()}
      >
        <ColumnsPlusLeft size={18} aria-hidden />
        <span>Добавить столбец</span>
      </button>
      <button
        type="button"
        role="menuitem"
        className={styles.dropdownItem}
        disabled={!editor.can().moveColumnLeft()}
        onMouseDown={(e) => e.preventDefault()}
        onClick={() => editor.chain().focus().moveColumnLeft().run()}
      >
        <ArrowLeft size={18} aria-hidden />
        <span>Столбец влево</span>
      </button>
      <button
        type="button"
        role="menuitem"
        className={styles.dropdownItem}
        disabled={!editor.can().moveColumnRight()}
        onMouseDown={(e) => e.preventDefault()}
        onClick={() => editor.chain().focus().moveColumnRight().run()}
      >
        <ArrowRight size={18} aria-hidden />
        <span>Столбец вправо</span>
      </button>
      <button
        type="button"
        role="menuitem"
        className={styles.dropdownItem}
        disabled={!editor.can().deleteRow()}
        onMouseDown={(e) => e.preventDefault()}
        onClick={() => editor.chain().focus().deleteRow().run()}
      >
        <Trash size={18} aria-hidden />
        <span>Удалить строку</span>
      </button>
      <button
        type="button"
        role="menuitem"
        className={styles.dropdownItem}
        disabled={!editor.can().deleteColumn()}
        onMouseDown={(e) => e.preventDefault()}
        onClick={() => editor.chain().focus().deleteColumn().run()}
      >
        <Trash size={18} aria-hidden />
        <span>Удалить столбец</span>
      </button>
      <button
        type="button"
        role="menuitem"
        className={`${styles.dropdownItem} ${styles.dropdownItemDanger}`}
        disabled={!editor.can().deleteTable()}
        onMouseDown={(e) => e.preventDefault()}
        onClick={() => {
          editor.chain().focus().deleteTable().run()
          onDone?.()
        }}
      >
        <Trash size={18} aria-hidden />
        <span>Удалить таблицу</span>
      </button>
    </>
  )
}
