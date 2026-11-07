import { useRef, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

import { useAnchoredMenuPosition } from '../../hooks/useAnchoredMenuPosition'
import { useClickOutside } from '../../hooks/useClickOutside'
import { useMenuKeyboardNav } from '../../hooks/useMenuKeyboardNav'
import { useDocumentActions } from '../../hooks/useDocumentActions'
import {
  IconCode,
  IconCopy,
  IconDotsThree,
  IconFiles,
  IconHistory,
  IconLink,
  IconStarMenu,
  IconTrashMenu,
} from '../icons/portalIcons'
import styles from '@/styles/modules/documents/DocumentActionsMenu.module.css'

const MENU_WIDTH = 220

type Props = {
  documentId: string
  title: string
  navNodeSlug?: string | null
  canEdit: boolean
  parentDocumentId?: string | null
  variant?: 'nav' | 'inline'
  extraItems?: ReactNode
  onHistoryOpen?: () => void
  onToast?: (message: string) => void
  onDeleted?: () => void
  onDeleteRevert?: () => void
  onDuplicated?: (newDocumentId: string) => void
  onPointerDownMenu?: (event: React.PointerEvent) => void
}

export function DocumentActionsMenu({
  documentId,
  title,
  navNodeSlug,
  canEdit,
  parentDocumentId,
  variant = 'inline',
  extraItems,
  onHistoryOpen,
  onToast,
  onDeleted,
  onDeleteRevert,
  onDuplicated,
  onPointerDownMenu,
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

  const actions = useDocumentActions({
    documentId,
    navNodeSlug,
    canEdit,
    parentDocumentId,
    onToast,
    onDeleted,
    onDeleteRevert,
    onDuplicated,
  })

  const rowClass = variant === 'nav' ? styles.navWrap : styles.inlineWrap

  function run(action: () => void) {
    setOpen(false)
    action()
  }

  const menu = open
    ? createPortal(
        <div
          ref={menuRef}
          className={styles.menuPortal}
          role="menu"
          aria-label={`Действия: ${title}`}
          style={{
            top: menuPos.top,
            left: menuPos.left,
            width: MENU_WIDTH,
            maxHeight: menuPos.maxHeight,
            overflowY: 'auto',
          }}
          onKeyDown={handleMenuKeyDown}
        >
          {extraItems}
          {onHistoryOpen ? (
            <button
              type="button"
              className={styles.menuItem}
              role="menuitem"
              onClick={() => run(onHistoryOpen)}
            >
              <IconHistory className={styles.menuItemIcon} />
              <span>Посмотреть историю изменений</span>
            </button>
          ) : null}
          {canEdit ? (
            <button
              type="button"
              className={`${styles.menuItem} ${styles.menuItemDanger}`}
              role="menuitem"
              disabled={actions.deletePending}
              onClick={() => run(actions.handleDelete)}
            >
              <IconTrashMenu className={styles.menuItemIcon} />
              <span>Удалить</span>
            </button>
          ) : null}
          <button
            type="button"
            className={styles.menuItem}
            role="menuitem"
            disabled={actions.favoritePending}
            onClick={() => run(actions.handleToggleFavorite)}
          >
            <IconStarMenu className={styles.menuItemIcon} filled={actions.isFavorite} />
            <span>{actions.isFavorite ? 'Убрать из избранного' : 'В избранное'}</span>
          </button>
          {canEdit ? (
            <button
              type="button"
              className={styles.menuItem}
              role="menuitem"
              disabled={actions.duplicatePending}
              onClick={() => run(actions.handleDuplicate)}
            >
              <IconCopy className={styles.menuItemIcon} />
              <span>Создать копию</span>
            </button>
          ) : null}
          {actions.canMoveToDeveloperDocs ? (
            <button
              type="button"
              className={styles.menuItem}
              role="menuitem"
              disabled={actions.moveSectionPending}
              onClick={() => run(actions.handleMoveToDeveloperDocs)}
            >
              <IconCode className={styles.menuItemIcon} />
              <span>В документы для разработчиков</span>
            </button>
          ) : null}
          {actions.canMoveToGeneralDocs ? (
            <button
              type="button"
              className={styles.menuItem}
              role="menuitem"
              disabled={actions.moveSectionPending}
              onClick={() => run(actions.handleMoveToGeneralDocs)}
            >
              <IconFiles className={styles.menuItemIcon} />
              <span>В общие документы</span>
            </button>
          ) : null}
          <button
            type="button"
            className={styles.menuItem}
            role="menuitem"
            onClick={() => run(actions.handleCopyLink)}
          >
            <IconLink className={styles.menuItemIcon} />
            <span>Копия ссылки</span>
          </button>
        </div>,
        document.body,
      )
    : null

  return (
    <div className={`${styles.root} ${rowClass}`}>
      <button
        ref={triggerRef}
        type="button"
        className={styles.menuBtn}
        title={`Действия: ${title}`}
        aria-label={`Действия: ${title}`}
        aria-expanded={open}
        aria-haspopup="menu"
        onClick={() => setOpen((v) => !v)}
        onKeyDown={handleTriggerKeyDown}
        onPointerDown={onPointerDownMenu}
        disabled={actions.deletePending || actions.duplicatePending}
      >
        <IconDotsThree />
      </button>
      {menu}
    </div>
  )
}
