import { useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Link } from 'react-router'

import { useAnchoredMenuPosition } from '../../../hooks/useAnchoredMenuPosition'
import { useClickOutside } from '../../../hooks/useClickOutside'
import { useMenuKeyboardNav } from '../../../hooks/useMenuKeyboardNav'
import { chatsPageHref } from '@/utils/chat/chatsNavigation'
import { IconDotsThree } from '../../icons/portalIcons'
import styles from '@/styles/modules/chat/ChatHeaderOverflowMenu.module.css'

const MENU_WIDTH = 200

type Props = {
  chatId: string
  /** Скрыть «Открыть в чатах» — на самой странице /chats переход не нужен. */
  showOpenInChats?: boolean
  onOpenInChatsNavigate?: () => void
  /** Показывать «Настройки» только для групповых чатов. */
  onOpenSettings?: () => void
  className?: string
}

/** Единая точка входа для второстепенных действий с чатом в хедере. */
export function ChatHeaderOverflowMenu({
  chatId,
  showOpenInChats = true,
  onOpenInChatsNavigate,
  onOpenSettings,
  className,
}: Props) {
  const [open, setOpen] = useState(false)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)
  const menuPos = useAnchoredMenuPosition(open, triggerRef, MENU_WIDTH, menuRef)

  useClickOutside(open, [triggerRef, menuRef], () => setOpen(false), 'mousedown')
  const { handleMenuKeyDown, handleTriggerKeyDown } = useMenuKeyboardNav(
    open,
    setOpen,
    triggerRef,
    menuRef,
  )

  function run(action: () => void) {
    setOpen(false)
    action()
  }

  const hasMenuItems = showOpenInChats || Boolean(onOpenSettings)
  if (!hasMenuItems) {
    return null
  }

  return (
    <div className={[styles.root, className].filter(Boolean).join(' ')}>
      <button
        ref={triggerRef}
        type="button"
        className={styles.menuBtn}
        aria-label="Действия с чатом"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        onKeyDown={handleTriggerKeyDown}
      >
        <IconDotsThree />
      </button>
      {open
        && createPortal(
          <div
            ref={menuRef}
            className={styles.menuPortal}
            role="menu"
            aria-label="Действия с чатом"
            style={{
              top: menuPos.top,
              left: menuPos.left,
              width: MENU_WIDTH,
              maxHeight: menuPos.maxHeight,
            }}
            onKeyDown={handleMenuKeyDown}
          >
            {showOpenInChats ? (
              <Link
                to={chatsPageHref(chatId)}
                className={styles.menuItem}
                role="menuitem"
                onClick={() => {
                  setOpen(false)
                  onOpenInChatsNavigate?.()
                }}
              >
                Открыть в чатах
              </Link>
            ) : null}
            {onOpenSettings ? (
              <button
                type="button"
                className={styles.menuItem}
                role="menuitem"
                onClick={() => run(onOpenSettings)}
              >
                Настройки
              </button>
            ) : null}
          </div>,
          document.body,
        )}
    </div>
  )
}
