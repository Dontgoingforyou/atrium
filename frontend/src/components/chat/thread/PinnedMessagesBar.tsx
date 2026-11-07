import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { listPinnedMessages, unpinMessage } from '../../../api/chat/chatApi'
import { portalPinnedMessagesQueryKey } from '../../../api/queryKeys'
import type { ChatMessage } from '../../../types/chat'
import { useNotifyToast } from '../../../hooks/useNotifyToast'
import { userFacingMessageFromUnknown } from '../../../utils/apiUserMessage'
import { IconPin } from '../../icons/portalIcons'
import styles from '@/styles/modules/chat/PinnedMessagesBar.module.css'

type Props = {
  chatId: string
  userMap?: Record<string, string>
  onJumpToMessage: (messageId: string) => void
}

/** Тонкая полоса закреплённых сообщений над историей чата. */
export function PinnedMessagesBar({ chatId, userMap = {}, onJumpToMessage }: Props) {
  const [index, setIndex] = useState(0)
  // Сброс индекса при смене чата — во время рендера (React docs: «Adjusting state when a
  // prop changes»), без эффекта, чтобы не ловить react-hooks/set-state-in-effect.
  const [prevChatId, setPrevChatId] = useState(chatId)
  if (chatId !== prevChatId) {
    setPrevChatId(chatId)
    setIndex(0)
  }
  const qc = useQueryClient()
  const notifyToast = useNotifyToast()
  const pinnedQueryKey = portalPinnedMessagesQueryKey(chatId)

  const { data, isError, error } = useQuery({
    queryKey: pinnedQueryKey,
    queryFn: () => listPinnedMessages(chatId),
    staleTime: 5_000,
  })

  const unpinMut = useMutation({
    mutationFn: (messageId: string) => unpinMessage(chatId, messageId),
    onSuccess: (_updated, messageId) => {
      qc.setQueryData<ChatMessage[]>(pinnedQueryKey, (prev) =>
        prev?.filter((m) => m.id !== messageId) ?? [],
      )
      qc.setQueriesData<ChatMessage[]>({ queryKey: ['portal', 'messages', chatId] }, (prev) =>
        prev?.map((m) => (m.id === messageId ? { ...m, pinned_at: null, pinned_by_sub: null } : m)) ?? prev,
      )
    },
    onError: (e: unknown) => notifyToast(userFacingMessageFromUnknown(e)),
  })

  if (isError) {
    return (
      <div className={styles.bar}>
        <span className={styles.icon} aria-hidden>
          <IconPin />
        </span>
        <p className={styles.snippet} role="alert">
          {userFacingMessageFromUnknown(error)}
        </p>
      </div>
    )
  }

  const pinned = data ?? []
  // Индекс может «протухнуть» после открепления/подгрузки — clamp прямо при рендере,
  // без второго эффекта только для синхронизации локального состояния.
  const safeIndex = pinned.length > 0 ? Math.min(index, pinned.length - 1) : 0

  if (pinned.length === 0) return null

  const current = pinned[safeIndex]
  const authorName = userMap[current.author_sub] ?? current.author_sub
  const snippet = current.body.trim() || (current.attachments?.length ? 'Вложение' : '')

  return (
    <div className={styles.bar}>
      <span className={styles.icon} aria-hidden>
        <IconPin />
      </span>
      <button
        type="button"
        className={styles.main}
        onClick={() => onJumpToMessage(current.id)}
        title="Перейти к закреплённому сообщению"
      >
        <span className={styles.label}>
          Закреплено{pinned.length > 1 ? ` (${safeIndex + 1}/${pinned.length})` : ''} — {authorName}
        </span>
        <span className={styles.snippet}>{snippet}</span>
      </button>
      {pinned.length > 1 && (
        <span className={styles.dots} aria-hidden>
          {pinned.map((p, i) => (
            <span
              key={p.id}
              className={`${styles.dot}${i === safeIndex ? ` ${styles.dotActive}` : ''}`}
            />
          ))}
        </span>
      )}
      {pinned.length > 1 && (
        <button
          type="button"
          className={styles.unpinBtn}
          aria-label="Следующее закреплённое сообщение"
          title="Следующее закреплённое сообщение"
          onClick={() => setIndex((safeIndex + 1) % pinned.length)}
        >
          ›
        </button>
      )}
      <button
        type="button"
        className={styles.unpinBtn}
        aria-label="Открепить сообщение"
        title="Открепить сообщение"
        disabled={unpinMut.isPending}
        onClick={() => unpinMut.mutate(current.id)}
      >
        ×
      </button>
    </div>
  )
}
