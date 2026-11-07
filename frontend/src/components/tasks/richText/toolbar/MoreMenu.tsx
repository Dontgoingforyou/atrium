import { useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import type { Editor } from '@tiptap/react'
import { Table, DotsThree } from '@phosphor-icons/react'
import styles from '@/styles/modules/tasks/RichTextEditorToolbar.module.css'
import { useAnchoredMenuPosition } from '@/hooks/useAnchoredMenuPosition'
import { useClickOutside } from '@/hooks/useClickOutside'
import { useMenuKeyboardNav } from '@/hooks/useMenuKeyboardNav'
import { useThemeStore } from '@/store/themeStore'
import MessageInputEmojiPanel from '../../../chat/composer/MessageInputEmojiPanel'

const MORE_MENU_WIDTH = 224
const MORE_MENU_WIDTH_WITH_EMOJI = 416

export function MoreMenu({ editor }: { editor: Editor | null }) {
  const [open, setOpen] = useState(false)
  const [emojiOpen, setEmojiOpen] = useState(false)
  const wrapRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)
  const theme = useThemeStore((s) => s.theme)
  const menuWidth = emojiOpen ? MORE_MENU_WIDTH_WITH_EMOJI : MORE_MENU_WIDTH
  const pos = useAnchoredMenuPosition(open, triggerRef, menuWidth, menuRef)

  useClickOutside(open, [wrapRef, menuRef], () => setOpen(false), 'mousedown')
  const { handleMenuKeyDown, handleTriggerKeyDown } = useMenuKeyboardNav(
    open,
    setOpen,
    triggerRef,
    menuRef,
  )

  return (
    <div className={styles.menuWrap} ref={wrapRef}>
      <button
        ref={triggerRef}
        type="button"
        tabIndex={-1}
        title="Ещё"
        aria-label="Ещё"
        aria-haspopup="menu"
        aria-expanded={open}
        className={`${styles.toolbarBtn} ${open ? styles.toolbarBtnActive : ''}`}
        onMouseDown={(e) => {
          e.preventDefault()
          setOpen((v) => !v)
        }}
        onKeyDown={handleTriggerKeyDown}
      >
        <DotsThree size={18} aria-hidden />
      </button>
      {open
        ? createPortal(
            <div
              ref={menuRef}
              className={`${styles.dropdownMenu} ${styles.dropdownMenuWide}`}
              role="menu"
              aria-label="Дополнительные действия"
              style={{ position: 'fixed', top: pos.top, left: pos.left }}
              onKeyDown={handleMenuKeyDown}
            >
              <button
                type="button"
                role="menuitem"
                className={styles.dropdownItem}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => {
                  editor?.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()
                  setOpen(false)
                }}
              >
                <Table size={18} aria-hidden />
                <span>Таблица 3×3</span>
              </button>
              <button
                type="button"
                role="menuitem"
                className={styles.dropdownItem}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => {
                  editor?.chain().focus().insertBuildinToggle().run()
                  setOpen(false)
                }}
              >
                <span>▶ Раскрывающийся блок</span>
              </button>
              <button
                type="button"
                role="menuitem"
                className={styles.dropdownItem}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => setEmojiOpen((v) => !v)}
              >
                <span>😀 Эмодзи</span>
              </button>
              {emojiOpen ? (
                <div className={styles.emojiPopoverInMenu}>
                  <MessageInputEmojiPanel
                    theme={theme}
                    perLine={12}
                    className={styles.emojiPickerWide}
                    onEmojiSelect={({ native }) => {
                      editor?.chain().focus().insertContent(native).run()
                      setEmojiOpen(false)
                      setOpen(false)
                    }}
                  />
                </div>
              ) : null}
            </div>,
            document.body,
          )
        : null}
    </div>
  )
}
