import type { UseMutationResult } from '@tanstack/react-query'
import type { VirtualItem } from '@tanstack/react-virtual'
import { useLayoutEffect, useRef } from 'react'

import { AttachmentItem } from '../composer/AttachmentItem'
import { ChatMessageReceiptIcon } from './ChatMessageReceiptIcon'
import { ReactionBar } from './ReactionBar'
import { UserAvatar } from '../../ui/UserAvatar'
import { IconDotsThree } from '../../icons/portalIcons'
import { HighlightedPlainText } from '../../search/HighlightedPlainText'
import type { ChatAttachment, ChatMessage } from '../../../types/chat'
import { dayDividerLabelForDate, sameCalendarDay, timeOnly } from '@/utils/chat/chatDate'
import {
  formatEmojiGameScoreCaption,
  parseEmojiGameScoreMessage,
  parseEmojiOnlyBody,
} from '@/utils/chat/emojiOnlyMessage'
import { getSelectedTextInElement } from '@/utils/chat/messageQuoteSelection'
import type { MenuState } from './MessageContextMenu'
import layout from '@/styles/modules/chat/ChatMessageListLayout.module.css'
import overlay from '@/styles/modules/chat/ChatMessageListOverlays.module.css'

type ReadersPopover = {
  messageId: string
  anchorRect: { top: number; bottom: number; left: number; right: number }
}

type PatchVars = { id: string; body: string }
type TranscribeVars = { messageId: string; attachmentId: string }

type Props = {
  virtualRow: VirtualItem
  measureElement: (el: HTMLElement | null) => void
  msg: ChatMessage
  messages: ChatMessage[]
  currentUserSub: string | null
  userMap: Record<string, string>
  userAvatarBySub: Record<string, string | undefined>
  editing: { id: string; body: string } | null
  setEditing: (v: { id: string; body: string } | null) => void
  busy: boolean
  patchMut: UseMutationResult<ChatMessage, Error, PatchVars, unknown>
  transcribeMut: UseMutationResult<ChatAttachment, Error, TranscribeVars, unknown>
  setMenu: (v: MenuState | null) => void
  setActionError: (v: string | null) => void
  setReadersPopover: (v: ReadersPopover | null) => void
  onOpenReactors: (messageId: string, emoji: string, anchorRect: DOMRect) => void
  onJumpToReply?: (messageId: string, quoteText?: string | null) => void
  /** Анимация удаления «для всех» перед исчезновением строки. */
  rowLeaving?: boolean
  /** Подсветка сообщения при переходе по deeplink из пуш-уведомления. */
  highlighted?: boolean
  /** Запрос из `?highlight=` — подсветка слов в теле сообщения. */
  highlightQuery?: string | null
  /** Подсветить непрерывный фрагмент (цитата ответа), а не токены поиска. */
  highlightExact?: boolean
  /** Открыть мини-игру по эмодзи из emoji-only сообщения. */
  onEmojiGameOpen?: (emojis: string[]) => void
  /** Якорь шага онбординга «Сообщения». */
  isTourAnchor?: boolean
  /** Якорь шага онбординга про пасхалку с эмодзи. */
  isTourEmojiAnchor?: boolean
}

export function ChatMessageListRow({
  virtualRow,
  measureElement,
  msg,
  messages,
  currentUserSub,
  userMap,
  userAvatarBySub,
  editing,
  setEditing,
  busy,
  patchMut,
  transcribeMut,
  setMenu,
  setActionError,
  setReadersPopover,
  onOpenReactors,
  onJumpToReply,
  rowLeaving = false,
  highlighted = false,
  highlightQuery = null,
  highlightExact = false,
  onEmojiGameOpen,
  isTourAnchor = false,
  isTourEmojiAnchor = false,
}: Props) {
  const idx = virtualRow.index
  const showDivider =
    idx === 0 || !sameCalendarDay(msg.created_at, messages[idx - 1].created_at)

  const isMine = msg.author_sub === currentUserSub
  const authorName = userMap[msg.author_sub] ?? '...'
  const time = timeOnly(msg.created_at)
  const showEdited =
    msg.updated_at != null
    && msg.created_at != null
    && msg.updated_at !== msg.created_at
  const isEditing = editing?.id === msg.id
  const editTextareaRef = useRef<HTMLTextAreaElement>(null)

  useLayoutEffect(() => {
    if (!isEditing) return
    const el = editTextareaRef.current
    if (!el || el.disabled) return
    el.focus({ preventScroll: true })
    const len = el.value.length
    el.setSelectionRange(len, len)
  }, [isEditing])

  // Крупная кнопка эмодзи — во всех чатах; онлайн-матч по-прежнему только в DM.
  const emojiOnly =
    !msg.deleted_for_all_at && msg.body ? parseEmojiOnlyBody(msg.body) : null
  const gameScore = msg.body && !msg.deleted_for_all_at
    ? parseEmojiGameScoreMessage(msg.body)
    : null
  const scoreAuthorLabel = isMine ? 'Вы' : authorName

  return (
    <div
      data-index={virtualRow.index}
      data-message-id={msg.id}
      {...(isTourAnchor ? { 'data-tour': 'chats-message-row' as const } : {})}
      ref={measureElement}
      className={`${layout.virtualItem}${rowLeaving ? ` ${layout.virtualItemLeaving}` : ''}`}
      style={{ transform: `translateY(${virtualRow.start}px)` }}
    >
      {showDivider && (
        <div className={layout.dayDivider}>
          <span className={layout.dayDividerLabel}>{dayDividerLabelForDate(msg.created_at)}</span>
        </div>
      )}
      <div
        className={`${layout.messageRow} ${isMine ? layout.messageRowMine : layout.messageRowOther}`}
      >
        {isEditing ? (
          <div className={`${layout.bubble} ${layout.bubbleMine} ${overlay.bubbleMine} ${layout.bubbleEdit}`}>
            <textarea
              ref={editTextareaRef}
              className={layout.editTextarea}
              value={editing.body}
              onChange={(e) => setEditing({ id: msg.id, body: e.target.value })}
              rows={3}
              disabled={busy}
            />
            <div className={layout.editActions}>
              <button
                type="button"
                className={layout.editCancel}
                disabled={busy}
                onClick={() => setEditing(null)}
              >
                Отмена
              </button>
              <button
                type="button"
                className={layout.editSave}
                disabled={busy || !editing.body.trim()}
                onClick={() => {
                  const b = editing.body.trim()
                  if (b) patchMut.mutate({ id: msg.id, body: b })
                }}
              >
                Сохранить
              </button>
            </div>
          </div>
        ) : (
          <div className={`${layout.bubbleRow} ${isMine ? layout.bubbleRowMine : layout.bubbleRowOther}`}>
            {!isMine && (
              <UserAvatar
                size={32}
                label={authorName}
                imageUrl={userAvatarBySub[msg.author_sub]}
                className={layout.msgSideAvatar}
              />
            )}
            {isMine && (
              <button
                type="button"
                className={layout.msgActionsBtn}
                data-tour-hover-action
                aria-label="Действия с сообщением"
                aria-haspopup="menu"
                onClick={(e) => {
                  e.stopPropagation()
                  const r = e.currentTarget.getBoundingClientRect()
                  setActionError(null)
                  setMenu({ x: r.right, y: r.bottom, message: msg, selectedQuote: null })
                }}
              >
                <IconDotsThree />
              </button>
            )}
            <div
              className={`${layout.bubble} ${isMine ? `${layout.bubbleMine} ${overlay.bubbleMine}` : layout.bubbleOther}${highlighted ? ` ${layout.bubbleHighlighted}` : ''}`}
              onContextMenu={(e) => {
                e.preventDefault()
                setActionError(null)
                const bodyEl = e.currentTarget.querySelector<HTMLElement>('[data-msg-body]')
                const quote = getSelectedTextInElement(bodyEl)
                setMenu({
                  x: e.clientX,
                  y: e.clientY,
                  message: msg,
                  selectedQuote: quote,
                })
              }}
            >
              {!isMine && <div className={layout.authorName}>{authorName}</div>}
              {msg.reply_to && (
                <div
                  role="button"
                  aria-label="Перейти к исходному сообщению"
                  tabIndex={0}
                  className={overlay.replyQuote}
                  onClick={(e) => {
                    e.stopPropagation()
                    // Не прыгать, если пользователь выделял текст именно в цитате.
                    if (getSelectedTextInElement(e.currentTarget)) return
                    const quote =
                      msg.reply_quote_text
                      || msg.reply_to!.quote_text
                      || null
                    onJumpToReply?.(msg.reply_to!.id, quote)
                  }}
                  onKeyDown={(e) => {
                    if (e.key !== 'Enter' && e.key !== ' ') return
                    e.preventDefault()
                    e.stopPropagation()
                    const quote =
                      msg.reply_quote_text
                      || msg.reply_to!.quote_text
                      || null
                    onJumpToReply?.(msg.reply_to!.id, quote)
                  }}
                >
                  <span className={overlay.replyQuoteAuthor}>
                    {userMap[msg.reply_to.author_sub] ?? '...'}
                  </span>
                  <span className={overlay.replyQuoteBody}>
                    {msg.reply_to.deleted_for_all_at
                      ? 'Сообщение удалено'
                      : (
                          msg.reply_quote_text
                          || msg.reply_to.quote_text
                          || msg.reply_to.body
                          || 'без текста'
                        )}
                  </span>
                </div>
              )}
              {msg.forwarded_from && (
                <div className={overlay.forwardHeader}>
                  Переслано от{' '}
                  <span className={overlay.forwardAuthor}>
                    {userMap[msg.forwarded_from.author_sub] ?? '...'}
                  </span>
                </div>
              )}
              {msg.body && (
                <div className={layout.bubbleBody} data-msg-body>
                  {gameScore ? (
                    <p
                      className={`${layout.scoreCaption} ${isMine ? layout.metaMine : layout.metaOther}`}
                    >
                      {formatEmojiGameScoreCaption(scoreAuthorLabel, gameScore.score)}
                    </p>
                  ) : emojiOnly && onEmojiGameOpen ? (
                    <button
                      type="button"
                      className={layout.emojiOnlyBtn}
                      aria-label="Открыть мини-игру"
                      {...(isTourEmojiAnchor
                        ? { 'data-tour': 'chats-emoji-easter' as const }
                        : {})}
                      onClick={(e) => {
                        e.stopPropagation()
                        onEmojiGameOpen(emojiOnly.emojis)
                      }}
                    >
                      {emojiOnly.emojis.join('')}
                    </button>
                  ) : (
                    <HighlightedPlainText
                      text={msg.body}
                      query={highlightQuery}
                      matchExact={highlightExact}
                    />
                  )}
                </div>
              )}
              {msg.attachments && msg.attachments.length > 0 && (
                <div className={layout.attachments}>
                  {msg.attachments.map((att) => (
                    <AttachmentItem
                      key={att.id}
                      att={att}
                      tone={isMine ? 'mine' : 'other'}
                      onTranscribe={() => transcribeMut.mutate({ messageId: msg.id, attachmentId: att.id })}
                      transcribing={
                        transcribeMut.isPending
                        && transcribeMut.variables?.attachmentId === att.id
                      }
                    />
                  ))}
                </div>
              )}
              <ReactionBar
                reactions={msg.reactions ?? []}
                busy={busy}
                onOpenReactors={(emoji, rect) => onOpenReactors(msg.id, emoji, rect)}
              />
              <div
                className={`${layout.meta} ${isMine ? layout.metaMine : layout.metaOther} ${
                  isMine ? layout.metaRowMine : ''
                }`}
              >
                <span>
                  {time}
                  {showEdited && <span className={layout.editedMark}> · изм.</span>}
                </span>
                {isMine && (
                  <ChatMessageReceiptIcon
                    receipt={msg.receipt ?? 'sent'}
                    onClick={(e) => {
                      e.stopPropagation()
                      const r = e.currentTarget.getBoundingClientRect()
                      setReadersPopover({
                        messageId: msg.id,
                        anchorRect: { top: r.top, bottom: r.bottom, left: r.left, right: r.right },
                      })
                    }}
                  />
                )}
              </div>
            </div>
            {!isMine && (
              <button
                type="button"
                className={layout.msgActionsBtn}
                data-tour-hover-action
                aria-label="Действия с сообщением"
                aria-haspopup="menu"
                onClick={(e) => {
                  e.stopPropagation()
                  const r = e.currentTarget.getBoundingClientRect()
                  setActionError(null)
                  setMenu({ x: r.right, y: r.bottom, message: msg, selectedQuote: null })
                }}
              >
                <IconDotsThree />
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
