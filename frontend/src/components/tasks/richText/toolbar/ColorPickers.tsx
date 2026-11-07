import { useEffect, useRef } from 'react'
import type { Editor } from '@tiptap/react'
import { Highlighter, Eraser } from '@phosphor-icons/react'
import styles from '@/styles/modules/tasks/RichTextEditorToolbar.module.css'
import { RICH_TEXT_DEFAULT_HIGHLIGHT_COLOR, RICH_TEXT_DEFAULT_TEXT_COLOR } from '../constants'

export function ColorPickers({ editor }: { editor: Editor | null }) {
  const colorApplyRafRef = useRef<number | null>(null)

  function scheduleColorApply(apply: () => void) {
    if (colorApplyRafRef.current != null) {
      cancelAnimationFrame(colorApplyRafRef.current)
    }
    colorApplyRafRef.current = requestAnimationFrame(() => {
      colorApplyRafRef.current = null
      apply()
    })
  }

  useEffect(() => {
    return () => {
      if (colorApplyRafRef.current != null) {
        cancelAnimationFrame(colorApplyRafRef.current)
      }
    }
  }, [])

  return (
    <>
      <label
        className={styles.colorLabel}
        title="Цвет текста"
        onMouseDown={(e) => e.preventDefault()}
      >
        <span className={styles.colorLabelText}>A</span>
        <input
          type="color"
          className={styles.colorInput}
          defaultValue={RICH_TEXT_DEFAULT_TEXT_COLOR}
          onMouseDown={(e) => e.preventDefault()}
          onChange={(e) => {
            const color = e.target.value
            scheduleColorApply(() => {
              editor?.chain().focus().setColor(color).run()
            })
          }}
        />
      </label>
      <button
        type="button"
        tabIndex={-1}
        title="Снять цвет текста"
        aria-label="Снять цвет текста"
        className={`${styles.toolbarBtn} ${editor?.getAttributes('textStyle').color ? styles.toolbarBtnActive : ''}`}
        onMouseDown={(e) => {
          e.preventDefault()
          editor?.chain().focus().extendMarkRange('textStyle').unsetColor().run()
        }}
      >
        <Eraser size={16} aria-hidden />
      </button>
      <label
        className={styles.colorLabel}
        title="Цвет маркера"
        onMouseDown={(e) => e.preventDefault()}
      >
        <Highlighter size={16} aria-hidden />
        <input
          type="color"
          className={styles.colorInput}
          defaultValue={RICH_TEXT_DEFAULT_HIGHLIGHT_COLOR}
          onMouseDown={(e) => e.preventDefault()}
          onChange={(e) => {
            const color = e.target.value
            scheduleColorApply(() => {
              editor?.chain().focus().setHighlight({ color }).run()
            })
          }}
        />
      </label>
      <button
        type="button"
        tabIndex={-1}
        title="Снять маркер"
        aria-label="Снять маркер"
        className={`${styles.toolbarBtn} ${editor?.isActive('highlight') ? styles.toolbarBtnActive : ''}`}
        onMouseDown={(e) => {
          e.preventDefault()
          editor?.chain().focus().extendMarkRange('highlight').unsetHighlight().run()
        }}
      >
        <Eraser size={16} weight="bold" aria-hidden />
      </button>
    </>
  )
}
