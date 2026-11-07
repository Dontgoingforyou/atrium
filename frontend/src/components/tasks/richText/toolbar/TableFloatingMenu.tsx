import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import type { Editor } from '@tiptap/react'
import { DotsThree } from '@phosphor-icons/react'
import { useAnchoredMenuPosition } from '../../../../hooks/useAnchoredMenuPosition'
import { useClickOutside } from '../../../../hooks/useClickOutside'
import { useMenuKeyboardNav } from '../../../../hooks/useMenuKeyboardNav'
import { TableActionsMenuItems } from './TableActionsMenuItems'
import {
  TABLE_FLOAT_SLOT_ATTR,
  findOrCreateTableFloatSlot,
  isTableFloatMenuTarget,
  resolveTableFloatWrapper,
  selectIntoTableWrapper,
} from './tableFloatingMenuDom'
import styles from '@/styles/modules/tasks/RichTextEditorTables.module.css'
import toolbarStyles from '@/styles/modules/tasks/RichTextEditorToolbar.module.css'

type Props = {
  editor: Editor
}

const TABLE_MENU_WIDTH = 224

export function TableFloatingMenu({ editor }: Props) {
  const [host, setHost] = useState<HTMLElement | null>(null)
  const [open, setOpen] = useState(false)
  const wrapRef = useRef<HTMLDivElement>(null)
  const btnRef = useRef<HTMLButtonElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)
  const menuPos = useAnchoredMenuPosition(open, btnRef, TABLE_MENU_WIDTH, menuRef)

  useClickOutside(open, [wrapRef, menuRef], () => setOpen(false))
  const { handleMenuKeyDown, handleTriggerKeyDown } = useMenuKeyboardNav(
    open,
    setOpen,
    btnRef,
    menuRef,
  )

  const openRef = useRef(false)
  useLayoutEffect(() => {
    openRef.current = open
  }, [open])

  const applyWrapper = useCallback((wrapper: HTMLElement | null) => {
    if (!wrapper) {
      if (openRef.current) return
      setHost(null)
      return
    }
    const next = findOrCreateTableFloatSlot(wrapper, styles.tableFloatSlot)
    setHost((prev) => {
      if (prev && prev !== next) setOpen(false)
      return next
    })
  }, [])

  const syncHost = useCallback(
    (event: MouseEvent | null = null) => {
      if (!editor.isEditable) {
        setHost(null)
        setOpen(false)
        return
      }
      if (event && isTableFloatMenuTarget(event.target)) return
      applyWrapper(resolveTableFloatWrapper(editor, event))
    },
    [applyWrapper, editor],
  )

  useLayoutEffect(() => {
    // Слот читается из DOM ProseMirror (курсор / hover), не из пропсов.
    // eslint-disable-next-line react-hooks/set-state-in-effect -- см. комментарий выше
    syncHost()
  }, [syncHost])

  useEffect(() => {
    const onUpdate = () => syncHost()
    const onMove = (event: MouseEvent) => syncHost(event)
    editor.on('selectionUpdate', onUpdate)
    editor.on('focus', onUpdate)
    window.addEventListener('mousemove', onMove, true)
    return () => {
      editor.off('selectionUpdate', onUpdate)
      editor.off('focus', onUpdate)
      window.removeEventListener('mousemove', onMove, true)
    }
  }, [editor, syncHost])

  useEffect(() => {
    return () => {
      document.querySelectorAll(`[${TABLE_FLOAT_SLOT_ATTR}]`).forEach((el) => el.remove())
    }
  }, [])

  if (!host) return null

  return (
    <>
      {createPortal(
        <div
          ref={wrapRef}
          className={styles.tableFloatWrap}
          data-table-float-menu
          onMouseDown={(e) => e.stopPropagation()}
          onPointerDown={(e) => e.stopPropagation()}
        >
          <button
            ref={btnRef}
            type="button"
            className={styles.tableFloatBtn}
            title="Действия с таблицей"
            aria-label="Действия с таблицей"
            aria-haspopup="menu"
            aria-expanded={open}
            onMouseDown={(e) => {
              e.preventDefault()
              e.stopPropagation()
              const wrapper = host.closest('.tableWrapper')
              if (wrapper instanceof HTMLElement) selectIntoTableWrapper(editor, wrapper)
              setOpen((v) => !v)
            }}
            onKeyDown={handleTriggerKeyDown}
          >
            <DotsThree size={18} weight="bold" aria-hidden />
          </button>
        </div>,
        host,
      )}
      {open
        ? createPortal(
            <div
              ref={menuRef}
              className={`${toolbarStyles.dropdownMenu} ${toolbarStyles.dropdownMenuWide} ${styles.tableFloatMenu}`}
              role="menu"
              aria-label="Действия с таблицей"
              data-table-float-menu
              onMouseDown={(e) => e.stopPropagation()}
              onPointerDown={(e) => e.stopPropagation()}
              onKeyDown={handleMenuKeyDown}
              style={{
                top: menuPos.top,
                left: menuPos.left,
                width: TABLE_MENU_WIDTH,
                maxHeight: menuPos.maxHeight,
                overflowY: 'auto',
              }}
            >
              <TableActionsMenuItems editor={editor} onDone={() => setOpen(false)} />
            </div>,
            document.body,
          )
        : null}
    </>
  )
}
