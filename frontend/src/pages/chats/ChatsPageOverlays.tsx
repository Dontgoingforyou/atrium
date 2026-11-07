import { useEffect, useRef } from 'react'

import { GroupChatSettingsModal } from '../../components/chat/common/GroupChatSettingsModal'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import type { Chat, PortalUser, UserPresence } from '../../types/chat'
import styles from '@/styles/modules/chat/ChatsPageThread.module.css'

type Props = {
  settingsOpen: boolean
  onCloseSettings: () => void
  activeChat: Chat | undefined
  currentUserSub: string | null
  portalUsers: PortalUser[]
  userMap: Record<string, string>
  presenceBySub: Record<string, UserPresence>
  onAfterSelfLeaveSettings: () => void
  chatCtxMenu: { x: number; y: number; chat: Chat } | null
  onDismissCtxMenu: () => void
  onPickDeleteFromCtxMenu: (chat: Chat) => void
  deleteConfirmChat: Chat | null
  onCancelDeleteConfirm: () => void
  deleteChatMutation: { isPending: boolean; mutate: (chatId: string) => void }
}

export function ChatsPageOverlays({
  settingsOpen,
  onCloseSettings,
  activeChat,
  currentUserSub,
  portalUsers,
  userMap,
  presenceBySub,
  onAfterSelfLeaveSettings,
  chatCtxMenu,
  onDismissCtxMenu,
  onPickDeleteFromCtxMenu,
  deleteConfirmChat,
  onCancelDeleteConfirm,
  deleteChatMutation,
}: Props) {
  const ctxMenuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!chatCtxMenu) return
    const menu = ctxMenuRef.current
    const focusable =
      menu?.querySelector<HTMLElement>('[role="menuitem"]:not(:disabled)') ??
      menu?.querySelector<HTMLElement>('[role="menuitem"]')
    focusable?.focus()
  }, [chatCtxMenu])

  useEffect(() => {
    if (!chatCtxMenu) return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        e.preventDefault()
        onDismissCtxMenu()
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [chatCtxMenu, onDismissCtxMenu])

  return (
    <>
      {settingsOpen && activeChat && !activeChat.is_direct && currentUserSub ? (
        <GroupChatSettingsModal
          key={activeChat.id}
          open={settingsOpen}
          onClose={onCloseSettings}
          chat={activeChat}
          currentUserSub={currentUserSub}
          portalUsers={portalUsers}
          userMap={userMap}
          presenceBySub={presenceBySub}
          onAfterSelfLeave={onAfterSelfLeaveSettings}
        />
      ) : null}

      {chatCtxMenu ? (
        document.documentElement.getAttribute('data-guided-tour') === '1' ? (
          <div
            ref={ctxMenuRef}
            className={styles.ctxMenu}
            data-tour-chat-ctx-menu
            style={{ left: chatCtxMenu.x, top: chatCtxMenu.y, position: 'fixed' }}
            role="menu"
            aria-label="Действия с чатом"
            tabIndex={-1}
          >
            <button type="button" className={styles.ctxMenuItem} role="menuitem" disabled>
              Удалить чат…
            </button>
          </div>
        ) : (
          <div
            className={styles.ctxMenuRoot}
            role="presentation"
            onClick={onDismissCtxMenu}
            onContextMenu={(ev) => {
              ev.preventDefault()
              onDismissCtxMenu()
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
            >
              <button
                type="button"
                className={styles.ctxMenuItem}
                role="menuitem"
                onClick={() => {
                  onPickDeleteFromCtxMenu(chatCtxMenu.chat)
                  onDismissCtxMenu()
                }}
              >
                Удалить чат…
              </button>
            </div>
          </div>
        )
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
          onCancel={onCancelDeleteConfirm}
        />
      ) : null}
    </>
  )
}
