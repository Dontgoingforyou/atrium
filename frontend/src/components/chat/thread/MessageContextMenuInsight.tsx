import { useEffect, useMemo, useRef, useState } from 'react'
import { useQueries, useQuery } from '@tanstack/react-query'

import { getMessageReaders, getMessageReactionReactors } from '../../../api/chat/chatApi'
import { messageReadersQueryKey, messageReactorsQueryKey } from '../../../api/queryKeys'
import { UserAvatar } from '../../ui/UserAvatar'
import type { ChatMessage } from '../../../types/chat'
import { insightAtLabel } from '@/utils/chat/chatDate'
import { mergeInsightRows, viewsLabel } from '@/utils/chat/messageInsight'
import styles from '@/styles/modules/chat/MessageContextMenu.module.css'

type Props = {
  chatId: string
  message: ChatMessage
  isMine: boolean
  menuLeft: number
  menuTop: number
  menuWidth: number
  userMap: Record<string, string>
  userAvatarBySub: Record<string, string | undefined>
}

export function MessageContextMenuInsight({
  chatId,
  message,
  isMine,
  menuLeft,
  menuTop,
  menuWidth,
  userMap,
  userAvatarBySub,
}: Props) {
  const m = message
  const reactions = m.reactions ?? []
  const hasReactions = reactions.length > 0
  const showViews = isMine
  const [open, setOpen] = useState(false)
  const closeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const insightBtnRef = useRef<HTMLButtonElement>(null)

  // Readers: сразу при «только просмотры» (для подписи N); иначе — при открытии панели.
  const { data: readers, isPending: readersPending, isError: readersError } = useQuery({
    queryKey: messageReadersQueryKey(chatId, m.id),
    queryFn: () => getMessageReaders(chatId, m.id),
    enabled: showViews && (open || !hasReactions),
    staleTime: 10_000,
  })

  const reactorQueries = useQueries({
    queries: reactions.map((r) => ({
      queryKey: messageReactorsQueryKey(chatId, m.id, r.emoji),
      queryFn: () => getMessageReactionReactors(chatId, m.id, r.emoji),
      enabled: open && hasReactions,
      staleTime: 10_000,
    })),
  })

  const reactorsDataKey = reactorQueries.map((q) => q.dataUpdatedAt).join('|')
  const reactorsError = reactorQueries.some((q) => q.isError)
  const reactorsPending =
    hasReactions && open && reactorQueries.some((q) => q.isPending || q.isFetching)

  const reactorsByEmoji = useMemo(
    () =>
      reactions.map((r, i) => ({
        emoji: r.emoji,
        reactors: reactorQueries[i]?.data ?? [],
      })),
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reactorsDataKey отражает обновление data
    [reactions, reactorsDataKey],
  )

  const rows = useMemo(
    () => mergeInsightRows(reactorsByEmoji, showViews ? readers : undefined),
    [reactorsByEmoji, readers, showViews],
  )

  const stackSubs = rows.slice(0, 3).map((r) => r.user_sub)

  const summaryLeft = (() => {
    if (hasReactions) {
      const emojis = reactions
        .slice(0, 2)
        .map((r) => r.emoji)
        .join('')
      return `${emojis} ${reactions.length}/3`
    }
    if (showViews) {
      const n = readers?.length
      return n == null ? 'Просмотрели' : viewsLabel(n)
    }
    return null
  })()

  useEffect(() => {
    return () => {
      if (closeTimerRef.current) clearTimeout(closeTimerRef.current)
    }
  }, [])

  function openPanel() {
    if (closeTimerRef.current) {
      clearTimeout(closeTimerRef.current)
      closeTimerRef.current = null
    }
    setOpen(true)
  }

  function scheduleClosePanel() {
    if (closeTimerRef.current) clearTimeout(closeTimerRef.current)
    closeTimerRef.current = setTimeout(() => setOpen(false), 160)
  }

  if (!summaryLeft) return null

  const panelMaxW = 260
  const gap = 6
  const margin = 8
  const panelW = Math.min(panelMaxW, window.innerWidth - margin * 2)
  const preferRight = menuLeft + menuWidth + gap + panelW <= window.innerWidth - margin
  const panelLeft = preferRight
    ? menuLeft + menuWidth + gap
    : Math.max(margin, menuLeft - gap - panelW)
  const btnTop = insightBtnRef.current?.getBoundingClientRect().top
  const panelTop = Math.max(
    margin,
    Math.min(btnTop ?? menuTop, window.innerHeight - margin - 120),
  )

  const panelLoading =
    (showViews && open && readersPending && readers === undefined) || reactorsPending
  const panelError =
    (showViews && open && readersError) || (hasReactions && open && reactorsError)

  return (
    <>
      <div className={styles.menuInsightSection}>
        <button
          ref={insightBtnRef}
          type="button"
          className={styles.menuInsight}
          role="menuitem"
          aria-expanded={open}
          aria-haspopup="dialog"
          onMouseEnter={openPanel}
          onMouseLeave={scheduleClosePanel}
          onFocus={openPanel}
          onClick={() => setOpen((v) => !v)}
        >
          <span className={styles.menuInsightLabel}>{summaryLeft}</span>
          {stackSubs.length > 0 && (
            <span className={styles.menuInsightAvatars} aria-hidden>
              {stackSubs.map((sub) => {
                const name = userMap[sub] ?? '…'
                return (
                  <span key={sub} className={styles.menuInsightAvatar}>
                    <UserAvatar
                      size={22}
                      label={name}
                      imageUrl={userAvatarBySub[sub]}
                      title={name}
                    />
                  </span>
                )
              })}
            </span>
          )}
        </button>
      </div>

      {open && (
        <div
          data-ctx-message-menu
          className={styles.menuInsightPanel}
          style={{ left: panelLeft, top: panelTop, width: panelW }}
          role="dialog"
          aria-label="Кто отреагировал и просмотрел"
          onMouseEnter={openPanel}
          onMouseLeave={scheduleClosePanel}
          onMouseDown={(e) => e.stopPropagation()}
          onClick={(e) => e.stopPropagation()}
        >
          {panelLoading ? (
            <div className={styles.menuInsightEmpty}>Загрузка…</div>
          ) : panelError ? (
            <div className={styles.menuInsightEmpty}>Не удалось загрузить</div>
          ) : rows.length === 0 ? (
            <div className={styles.menuInsightEmpty}>
              {hasReactions ? 'Пока никого' : 'Никто ещё не просмотрел'}
            </div>
          ) : (
            rows.map((row) => {
              const name = userMap[row.user_sub] ?? '…'
              return (
                <div
                  key={`${row.kind}-${row.user_sub}-${row.emoji ?? ''}`}
                  className={styles.menuInsightRow}
                >
                  <UserAvatar
                    size={32}
                    label={name}
                    imageUrl={userAvatarBySub[row.user_sub]}
                    className={styles.menuInsightRowAvatar}
                  />
                  <div className={styles.menuInsightRowBody}>
                    <div className={styles.menuInsightRowName}>{name}</div>
                    <div className={styles.menuInsightRowMeta}>
                      <span className={styles.menuInsightRowMetaIcon} aria-hidden>
                        {row.kind === 'reaction' ? row.emoji : '✓✓'}
                      </span>
                      {insightAtLabel(row.at)}
                    </div>
                  </div>
                  {row.kind === 'reaction' && row.emoji ? (
                    <span className={styles.menuInsightRowEmoji} aria-hidden>
                      {row.emoji}
                    </span>
                  ) : null}
                </div>
              )
            })
          )}
        </div>
      )}
    </>
  )
}
