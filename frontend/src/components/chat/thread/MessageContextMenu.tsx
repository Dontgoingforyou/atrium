import { lazy, Suspense, useEffect, useRef } from 'react'

import type { Chat, ChatMessage } from '../../../types/chat'
import { getQuickReactionEmojis } from '@/utils/chat/chatReactionFrequent'
import { MessageContextMenuInsight } from './MessageContextMenuInsight'
import styles from '@/styles/modules/chat/MessageContextMenu.module.css'

const MessageInputEmojiPanel = lazy(() => import('../composer/MessageInputEmojiPanel'))

export type MenuState = {
  x: number
  y: number
  message: ChatMessage
  selectedQuote?: string | null
}

type CtxEmojiPicker = {
  messageId: string
  anchorTop: number
  anchorBottom: number
  anchorLeft: number
}

type Props = {
  menu: MenuState
  chatId: string
  currentUserSub: string | null
  chatsForForward: Chat[]
  busy: boolean
  theme: string
  ctxEmojiPicker: CtxEmojiPicker | null
  userMap?: Record<string, string>
  userAvatarBySub?: Record<string, string | undefined>
  onClose: () => void
  onReply?: (message: ChatMessage, quoteText?: string) => void
  onEdit: (id: string, body: string) => void
  onDeleteMe: (id: string) => void
  onDeleteAll: (id: string) => void
  onForward: (message: ChatMessage) => void
  onReactionToggle: (messageId: string, emoji: string) => Promise<void>
  onEmojiPickerToggle: (picker: CtxEmojiPicker | null) => void
  onPinToggle?: (message: ChatMessage) => void
}

function ctxEmojiPopoverPos(a: { anchorTop: number; anchorBottom: number; anchorLeft: number }) {
  const estH = 300
  const margin = 8
  let top = a.anchorBottom + 4
  if (top + estH > window.innerHeight - margin) {
    top = Math.max(margin, a.anchorTop - estH - 4)
  }
  const popW = 360
  const left = Math.max(margin, Math.min(a.anchorLeft, window.innerWidth - popW - margin))
  return { top, left }
}

export function MessageContextMenu({
  menu,
  chatId,
  currentUserSub,
  chatsForForward,
  busy,
  theme,
  ctxEmojiPicker,
  userMap = {},
  userAvatarBySub = {},
  onClose,
  onReply,
  onEdit,
  onDeleteMe,
  onDeleteAll,
  onForward,
  onReactionToggle,
  onEmojiPickerToggle,
  onPinToggle,
}: Props) {
  const m = menu.message
  const isMine = m.author_sub === currentUserSub
  const isDeleted = m.deleted_for_all_at != null
  const w = 240
  const h = 320
  const left = Math.min(menu.x, window.innerWidth - w - 8)
  const top = Math.min(menu.y, window.innerHeight - h - 8)
  const strip = getQuickReactionEmojis().slice(0, 7)
  const reactions = m.reactions ?? []
  const uniqueEmojiCount = reactions.length
  const limitReached = uniqueEmojiCount >= 3
  const menuRef = useRef<HTMLDivElement>(null)
  const showInsight = !isDeleted && (isMine || reactions.length > 0)

  useEffect(() => {
    const firstItem = menuRef.current?.querySelector<HTMLElement>('[role="menuitem"]:not(:disabled)')
    firstItem?.focus()
  }, [])

  function handleMenuKeyDown(e: React.KeyboardEvent<HTMLDivElement>) {
    if (e.key === 'Escape') {
      onClose()
      return
    }
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault()
      const items = Array.from(
        menuRef.current?.querySelectorAll<HTMLElement>('[role="menuitem"]:not(:disabled)') ?? [],
      )
      if (!items.length) return
      const idx = items.indexOf(document.activeElement as HTMLElement)
      if (e.key === 'ArrowDown') {
        items[(idx + 1) % items.length]?.focus()
      } else {
        items[(idx - 1 + items.length) % items.length]?.focus()
      }
    }
    if (e.key === 'Home') {
      e.preventDefault()
      const items = Array.from(
        menuRef.current?.querySelectorAll<HTMLElement>('[role="menuitem"]:not(:disabled)') ?? [],
      )
      items[0]?.focus()
    }
    if (e.key === 'End') {
      e.preventDefault()
      const items = Array.from(
        menuRef.current?.querySelectorAll<HTMLElement>('[role="menuitem"]:not(:disabled)') ?? [],
      )
      items[items.length - 1]?.focus()
    }
  }

  return (
    <>
      <div
        ref={menuRef}
        data-ctx-message-menu
        className={styles.contextMenu}
        style={{ left, top, width: w }}
        role="menu"
        aria-label="Действия с сообщением"
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
        onKeyDown={handleMenuKeyDown}
      >
        {!isDeleted && (
          <div className={styles.contextMenuReactions} role="group" aria-label="Быстрые реакции">
            {strip.map((emoji) => {
              const alreadyOnMsg = reactions.some((r) => r.emoji === emoji)
              return (
                <button
                  key={emoji}
                  type="button"
                  className={styles.contextMenuReactionBtn}
                  title={
                    limitReached && !alreadyOnMsg
                      ? 'Достигнут лимит реакций (3 уникальных)'
                      : emoji
                  }
                  aria-label={`Поставить реакцию ${emoji}`}
                  disabled={busy || (limitReached && !alreadyOnMsg)}
                  onClick={() => {
                    void (async () => {
                      try {
                        await onReactionToggle(m.id, emoji)
                        onClose()
                      } catch {
                        /* actionError в родителе */
                      }
                    })()
                  }}
                >
                  {emoji}
                </button>
              )
            })}
            <button
              type="button"
              className={styles.contextMenuReactionPlus}
              title={limitReached ? 'Достигнут лимит реакций (3 уникальных)' : 'Другие эмодзи'}
              aria-label="Другие эмодзи"
              disabled={busy || limitReached}
              onClick={(e) => {
                e.stopPropagation()
                const r = e.currentTarget.getBoundingClientRect()
                onEmojiPickerToggle(
                  ctxEmojiPicker?.messageId === m.id
                    ? null
                    : {
                        messageId: m.id,
                        anchorTop: r.top,
                        anchorBottom: r.bottom,
                        anchorLeft: r.left,
                      },
                )
              }}
            >
              +
            </button>
          </div>
        )}
        {!isDeleted && onReply && (
          <button
            type="button"
            className={styles.menuItem}
            role="menuitem"
            disabled={busy}
            onClick={() => {
              onReply(m)
              onClose()
            }}
          >
            Ответить
          </button>
        )}
        {!isDeleted && onReply && menu.selectedQuote && (
          <button
            type="button"
            className={styles.menuItem}
            role="menuitem"
            disabled={busy}
            onClick={() => {
              onReply(m, menu.selectedQuote!)
              onClose()
            }}
          >
            Ответить с цитатой
          </button>
        )}
        {!isDeleted && (
          <button
            type="button"
            className={styles.menuItem}
            role="menuitem"
            disabled={busy || chatsForForward.length === 0}
            title={
              chatsForForward.length === 0
                ? 'Создайте или откройте ещё один чат, чтобы пересылать сообщения'
                : undefined
            }
            onClick={() => {
              if (chatsForForward.length === 0) return
              onForward(m)
              onClose()
            }}
          >
            Переслать…
          </button>
        )}
        {isMine && !isDeleted && (
          <button
            type="button"
            className={styles.menuItem}
            role="menuitem"
            disabled={busy}
            onClick={() => {
              onEdit(m.id, m.body)
              onClose()
            }}
          >
            Изменить
          </button>
        )}
        {!isDeleted && onPinToggle && (
          <button
            type="button"
            className={styles.menuItem}
            role="menuitem"
            disabled={busy}
            onClick={() => {
              onPinToggle(m)
              onClose()
            }}
          >
            {m.pinned_at ? 'Открепить' : 'Закрепить'}
          </button>
        )}
        {!isDeleted && (
          <button
            type="button"
            className={styles.menuItem}
            role="menuitem"
            disabled={busy}
            onClick={() => onDeleteMe(m.id)}
          >
            Удалить только у меня
          </button>
        )}
        {isMine && !isDeleted && (
          <button
            type="button"
            className={styles.menuItem}
            role="menuitem"
            disabled={busy}
            onClick={() => onDeleteAll(m.id)}
          >
            Удалить у всех
          </button>
        )}

        {showInsight && (
          <MessageContextMenuInsight
            chatId={chatId}
            message={m}
            isMine={isMine}
            menuLeft={left}
            menuTop={top}
            menuWidth={w}
            userMap={userMap}
            userAvatarBySub={userAvatarBySub}
          />
        )}
      </div>

      {ctxEmojiPicker && (
        <div
          data-ctx-emoji-popover
          className={styles.contextMenuEmojiPopover}
          style={{
            position: 'fixed',
            zIndex: 12050,
            ...ctxEmojiPopoverPos(ctxEmojiPicker),
          }}
          role="dialog"
          aria-label="Выбор эмодзи"
          onMouseDown={(e) => e.stopPropagation()}
          onClick={(e) => e.stopPropagation()}
        >
          <Suspense
            fallback={
              <div className={styles.reactionPickerFallback} role="status">
                Загрузка…
              </div>
            }
          >
            <MessageInputEmojiPanel
              theme={theme === 'dark' ? 'dark' : 'light'}
              onEmojiSelect={(data) => {
                void (async () => {
                  try {
                    await onReactionToggle(ctxEmojiPicker.messageId, data.native)
                    onClose()
                  } catch {
                    /* actionError */
                  }
                })()
              }}
            />
          </Suspense>
        </div>
      )}
    </>
  )
}
