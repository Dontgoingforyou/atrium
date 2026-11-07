import { useEffect, useRef, type KeyboardEvent } from 'react'
import type { Chat, PortalUser, UserPresence } from '../../../types/chat'
import { ConfirmDialog } from '../../ui/ConfirmDialog'
import { GroupChatSettingsModal } from '../common/GroupChatSettingsModal'
import styles from '@/styles/modules/chat/FloatingDmWidgetPicker.module.css'

type Props = {
  groupSettingsOpen: boolean
  activeChat: Chat | undefined
  currentUserSub: string | null
  portalUsers: PortalUser[]
  userMap: Record<string, string>
  presenceBySub: Record<string, UserPresence>
  onCloseGroupSettings: () => void
  onAfterSelfLeave: () => void
  chatCtxMenu: { x: number; y: number; chat: Chat } | null
  onCloseCtxMenu: () => void
  onRequestDeleteFromCtx: (chat: Chat) => void
  deleteConfirmChat: Chat | null
  deleteChatMutation: {
    isPending: boolean
    mutate: (chatId: string) => void
  }
  onCancelDelete: () => void
}

const CTX_MENUITEM_SELECTOR = '[role="menuitem"]:not([disabled])'

/** Оверлеи виджета ЛС: настройки группы, контекстное меню, подтверждение удаления. */
export function FloatingDmWidgetOverlays({
  groupSettingsOpen,
  activeChat,
  currentUserSub,
  portalUsers,
  userMap,
  presenceBySub,
  onCloseGroupSettings,
  onAfterSelfLeave,
  chatCtxMenu,
  onCloseCtxMenu,
  onRequestDeleteFromCtx,
  deleteConfirmChat,
  deleteChatMutation,
  onCancelDelete,
}: Props) {
  const ctxMenuRef = useRef<HTMLDivElement>(null)

  const ctxOpen = chatCtxMenu !== null
  useEffect(() => {
    if (!ctxOpen) return
    const item = ctxMenuRef.current?.querySelector<HTMLElement>(CTX_MENUITEM_SELECTOR)
    item?.focus()
  }, [ctxOpen])

  function handleCtxMenuKeyDown(e: KeyboardEvent<HTMLDivElement>): void {
    const items = ctxMenuRef.current?.querySelectorAll<HTMLElement>(CTX_MENUITEM_SELECTOR)
    const list = items ? Array.from(items) : []
    if (list.length === 0) return
    const currentIndex = list.findIndex((el) => el === document.activeElement)
    const focusAt = (idx: number) => list[(idx + list.length) % list.length]?.focus()
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        focusAt(currentIndex < 0 ? 0 : currentIndex + 1)
        break
      case 'ArrowUp':
        e.preventDefault()
        focusAt(currentIndex < 0 ? 0 : currentIndex - 1)
        break
      case 'Enter':
      case ' ':
      case 'Spacebar':
        if (currentIndex >= 0) {
          e.preventDefault()
          ;(list[currentIndex] as HTMLElement).click()
        }
        break
      case 'Escape':
        e.preventDefault()
        onCloseCtxMenu()
        break
    }
  }

  return (
    <>
      {groupSettingsOpen && activeChat && !activeChat.is_direct && currentUserSub ? (
        <GroupChatSettingsModal
          key={activeChat.id}
          open={groupSettingsOpen}
          onClose={onCloseGroupSettings}
          chat={activeChat}
          currentUserSub={currentUserSub}
          portalUsers={portalUsers}
          userMap={userMap}
          presenceBySub={presenceBySub}
          onAfterSelfLeave={onAfterSelfLeave}
        />
      ) : null}

      {chatCtxMenu ? (
        <div
          className={styles.ctxMenuRoot}
          role="presentation"
          onClick={onCloseCtxMenu}
          onContextMenu={(ev) => {
            ev.preventDefault()
            onCloseCtxMenu()
          }}
        >
          <div
            ref={ctxMenuRef}
            className={styles.ctxMenu}
            style={{ left: chatCtxMenu.x, top: chatCtxMenu.y }}
            role="menu"
            aria-label="Действия с чатом"
            tabIndex={-1}
            onClick={(ev) => ev.stopPropagation()}
            onKeyDown={handleCtxMenuKeyDown}
          >
            <button
              type="button"
              className={styles.ctxMenuItem}
              role="menuitem"
              onClick={() => {
                onRequestDeleteFromCtx(chatCtxMenu.chat)
                onCloseCtxMenu()
              }}
            >
              Удалить чат…
            </button>
          </div>
        </div>
      ) : null}

      {deleteConfirmChat ? (
        <ConfirmDialog
          open
          title="Удалить чат"
          message={
            deleteConfirmChat.is_direct
              ? 'Удалить этот диалог для обоих участников? История сообщений будет безвозвратно удалена.'
              : 'Удалить групповой чат для всех участников? История и вложения будут безвозвратно удалены.'
          }
          confirmLabel="Удалить"
          cancelLabel="Отмена"
          destructive
          confirmSound="error"
          disabled={deleteChatMutation.isPending}
          onConfirm={() => deleteChatMutation.mutate(deleteConfirmChat.id)}
          onCancel={onCancelDelete}
        />
      ) : null}
    </>
  )
}
