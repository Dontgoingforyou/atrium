import { useCallback, useEffect, useId, useMemo, useRef, useState } from 'react'

import type { Chat } from '../../../types/chat'
import { chatDisplayName } from '@/utils/chat/chatDisplay'
import { useBodyScrollLock } from '../../../hooks/useBodyScrollLock'
import { useFocusTrap } from '../../../hooks/useFocusTrap'
import styles from '@/styles/modules/chat/ForwardToChatModal.module.css'

type Props = {
  open: boolean
  onClose: () => void
  chats: Chat[]
  currentUserSub: string | null
  userMap: Record<string, string>
  onSelect: (chatId: string) => void
  busy?: boolean
}

export function ForwardToChatModal({
  open,
  onClose,
  chats,
  currentUserSub,
  userMap,
  onSelect,
  busy = false,
}: Props) {
  const [q, setQ] = useState('')
  const dialogRef = useRef<HTMLDivElement>(null)
  const closeRef = useRef<HTMLButtonElement>(null)
  const titleId = useId()

  const handleClose = useCallback(() => {
    setQ('')
    onClose()
  }, [onClose])

  const handleSelect = useCallback(
    (chatId: string) => {
      setQ('')
      onSelect(chatId)
    },
    [onSelect],
  )

  useFocusTrap(dialogRef, open)
  useBodyScrollLock(open)

  useEffect(() => {
    if (!open) return
    closeRef.current?.focus()
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        e.preventDefault()
        handleClose()
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, handleClose])

  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase()
    if (!s) return chats
    return chats.filter((c) => chatDisplayName(c, currentUserSub, userMap).toLowerCase().includes(s))
  }, [chats, q, currentUserSub, userMap])

  if (!open) return null

  return (
    <div className={styles.overlay} role="presentation" onClick={handleClose}>
      <div
        ref={dialogRef}
        className={styles.modal}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id={titleId} className={styles.title}>
          Переслать в чат
        </h2>
        <input
          type="search"
          className={styles.search}
          placeholder="Поиск…"
          aria-label="Поиск чата"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <ul className={styles.list}>
          {filtered.map((c) => (
            <li key={c.id}>
              <button
                type="button"
                className={styles.item}
                disabled={busy}
                onClick={() => handleSelect(c.id)}
              >
                {chatDisplayName(c, currentUserSub, userMap)}
              </button>
            </li>
          ))}
        </ul>
        {filtered.length === 0 ? <p className={styles.empty}>Нет подходящих чатов</p> : null}
        <button ref={closeRef} type="button" className={styles.closeBtn} onClick={handleClose}>
          Отмена
        </button>
      </div>
    </div>
  )
}
