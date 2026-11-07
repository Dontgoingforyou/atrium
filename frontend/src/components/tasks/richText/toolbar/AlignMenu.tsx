import { useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import type { Editor } from '@tiptap/react'
import {
  TextAlignLeft,
  TextAlignCenter,
  TextAlignRight,
  TextAlignJustify,
  CaretDown,
} from '@phosphor-icons/react'
import styles from '@/styles/modules/tasks/RichTextEditorToolbar.module.css'
import { useAnchoredMenuPosition } from '@/hooks/useAnchoredMenuPosition'
import { useClickOutside } from '@/hooks/useClickOutside'
import { useMenuKeyboardNav } from '@/hooks/useMenuKeyboardNav'
import { ALIGNMENT_OPTIONS } from '../constants'

const ALIGN_MENU_WIDTH = 180

const ALIGN_ICONS = {
  left: TextAlignLeft,
  center: TextAlignCenter,
  right: TextAlignRight,
  justify: TextAlignJustify,
} as const

export function AlignMenu({ editor }: { editor: Editor | null }) {
  const [open, setOpen] = useState(false)
  const wrapRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)
  const pos = useAnchoredMenuPosition(open, triggerRef, ALIGN_MENU_WIDTH, menuRef)

  useClickOutside(open, [wrapRef, menuRef], () => setOpen(false), 'mousedown')
  const { handleMenuKeyDown, handleTriggerKeyDown } = useMenuKeyboardNav(
    open,
    setOpen,
    triggerRef,
    menuRef,
  )

  const align =
    ALIGNMENT_OPTIONS.find((a) => editor?.isActive({ textAlign: a.value }))?.value ?? 'left'

  const AlignIcon =
    align === 'center'
      ? TextAlignCenter
      : align === 'right'
        ? TextAlignRight
        : align === 'justify'
          ? TextAlignJustify
          : TextAlignLeft

  return (
    <div className={styles.menuWrap} ref={wrapRef}>
      <button
        ref={triggerRef}
        type="button"
        tabIndex={-1}
        title="Выравнивание"
        aria-label="Выравнивание"
        aria-haspopup="menu"
        aria-expanded={open}
        className={`${styles.toolbarBtn} ${styles.toolbarBtnCombo} ${open ? styles.toolbarBtnActive : ''}`}
        onMouseDown={(e) => {
          e.preventDefault()
          setOpen((v) => !v)
        }}
        onKeyDown={handleTriggerKeyDown}
      >
        <AlignIcon size={16} aria-hidden />
        <CaretDown size={12} aria-hidden />
      </button>
      {open
        ? createPortal(
            <div
              ref={menuRef}
              className={`${styles.dropdownMenu} ${styles.dropdownMenuAlignGrid}`}
              role="menu"
              aria-label="Выравнивание текста"
              style={{ position: 'fixed', top: pos.top, left: pos.left }}
              onKeyDown={handleMenuKeyDown}
            >
              {ALIGNMENT_OPTIONS.map((a) => {
                const Icon = ALIGN_ICONS[a.value]
                return (
                  <button
                    key={a.value}
                    type="button"
                    role="menuitem"
                    title={a.title}
                    aria-label={a.title}
                    className={`${styles.dropdownAlignBtn} ${align === a.value ? styles.dropdownAlignBtnActive : ''}`}
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => {
                      editor?.chain().focus().setTextAlign(a.value).run()
                      setOpen(false)
                    }}
                  >
                    <Icon size={20} weight="bold" aria-hidden />
                  </button>
                )
              })}
            </div>,
            document.body,
          )
        : null}
    </div>
  )
}
