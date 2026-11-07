import { useCallback, useEffect, useId, useRef, useState } from 'react'
import { useInfiniteQuery } from '@tanstack/react-query'

import { listChatAttachments, type ChatAttachmentKind } from '../../../api/chat/chatApi'
import type { ChatAttachment } from '../../../types/chat'
import { useStableImageUrl } from '../../../hooks/useStableImageUrl'
import { useBodyScrollLock } from '../../../hooks/useBodyScrollLock'
import { useFocusTrap } from '../../../hooks/useFocusTrap'
import { dayDividerLabelForDate, timeOnly } from '@/utils/chat/chatDate'
import { fileIcon, formatBytes } from '../../../utils/fileUtils'
import { MediaLightbox } from '../../ui/MediaLightbox'
import styles from '@/styles/modules/chat/ChatAttachmentsGalleryModal.module.css'

const PAGE_LIMIT = 30

const TABS: { kind: ChatAttachmentKind; label: string }[] = [
  { kind: 'media', label: 'Медиа' },
  { kind: 'file', label: 'Файлы' },
  { kind: 'audio', label: 'Голосовые' },
]

type Props = {
  open: boolean
  chatId: string
  onClose: () => void
  /** Закрывает галерею и переводит фокус на сообщение (deep-link через message_id вложения). */
  onJumpToMessage: (messageId: string) => void
}

function MediaGalleryTile({
  att,
  onPreview,
}: {
  att: ChatAttachment
  onPreview: () => void
}) {
  const isVideo = att.content_type.startsWith('video/')
  const stableUrl = useStableImageUrl(isVideo ? undefined : att.download_url)

  return (
    <button
      type="button"
      className={styles.mediaTile}
      onClick={onPreview}
      title={att.original_filename}
    >
      {isVideo ? (
        <>
          <video className={styles.mediaTileMedia} src={att.download_url} muted preload="metadata" />
          <span className={styles.mediaTilePlayBadge} aria-hidden>▶</span>
        </>
      ) : stableUrl ? (
        <img className={styles.mediaTileMedia} src={stableUrl} alt={att.original_filename} loading="lazy" />
      ) : null}
    </button>
  )
}

function FileGalleryRow({ att, onJump }: { att: ChatAttachment; onJump: () => void }) {
  return (
    <div className={styles.row}>
      <span className={styles.rowIcon} aria-hidden>{fileIcon(att.content_type)}</span>
      <div className={styles.rowMain}>
        <span className={styles.rowName} title={att.original_filename}>{att.original_filename}</span>
        <span className={styles.rowMeta}>
          {formatBytes(att.file_size)} · {dayDividerLabelForDate(att.created_at)}, {timeOnly(att.created_at)}
        </span>
      </div>
      <div className={styles.rowActions}>
        <a
          className={styles.rowLinkBtn}
          href={att.download_url}
          target="_blank"
          rel="noopener noreferrer"
          download={att.original_filename}
        >
          Скачать
        </a>
        <button type="button" className={styles.rowLinkBtn} onClick={onJump}>
          К сообщению
        </button>
      </div>
    </div>
  )
}

function VoiceGalleryRow({ att, onJump }: { att: ChatAttachment; onJump: () => void }) {
  return (
    <div className={styles.row}>
      <span className={styles.rowIcon} aria-hidden>🎤</span>
      <div className={styles.rowMain}>
        <audio className={styles.rowAudio} controls preload="metadata" src={att.download_url} />
        <span className={styles.rowMeta}>
          {dayDividerLabelForDate(att.created_at)}, {timeOnly(att.created_at)}
        </span>
        {att.transcript ? <span className={styles.rowTranscript}>{att.transcript}</span> : null}
      </div>
      <div className={styles.rowActions}>
        <button type="button" className={styles.rowLinkBtn} onClick={onJump}>
          К сообщению
        </button>
      </div>
    </div>
  )
}

/** Отдельная галерея вложений чата — «провалиться» без скролла всей истории. */
export function ChatAttachmentsGalleryModal({ open, chatId, onClose, onJumpToMessage }: Props) {
  const [tab, setTab] = useState<ChatAttachmentKind>('media')
  const [previewAtt, setPreviewAtt] = useState<ChatAttachment | null>(null)
  const dialogRef = useRef<HTMLDivElement>(null)
  const closeRef = useRef<HTMLButtonElement>(null)
  const titleId = useId()
  const nestedOpen = previewAtt !== null

  const handleGalleryClose = useCallback(() => {
    if (previewAtt) {
      setPreviewAtt(null)
      return
    }
    onClose()
  }, [previewAtt, onClose])

  useFocusTrap(dialogRef, open && !nestedOpen)
  useBodyScrollLock(open)

  useEffect(() => {
    if (!open || nestedOpen) return
    closeRef.current?.focus()
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        e.preventDefault()
        handleGalleryClose()
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, nestedOpen, handleGalleryClose])

  const { data, isLoading, isError, fetchNextPage, hasNextPage, isFetchingNextPage } = useInfiniteQuery({
    queryKey: ['portal', 'chat-attachments', chatId, tab],
    queryFn: ({ pageParam }) => listChatAttachments(chatId, { kind: tab, skip: pageParam, limit: PAGE_LIMIT }),
    initialPageParam: 0,
    getNextPageParam: (lastPage, pages) => {
      const loaded = pages.reduce((sum, p) => sum + p.items.length, 0)
      return loaded < lastPage.total ? loaded : undefined
    },
    enabled: open,
  })

  if (!open) return null

  const items = data?.pages.flatMap((p) => p.items) ?? []

  function jump(messageId: string | null | undefined) {
    if (!messageId) return
    setPreviewAtt(null)
    onClose()
    onJumpToMessage(messageId)
  }

  return (
    <div className={styles.overlay} role="presentation" onClick={handleGalleryClose}>
      <div
        ref={dialogRef}
        className={styles.modal}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onClick={(e) => e.stopPropagation()}
      >
        <div className={styles.header}>
          <h2 id={titleId} className={styles.title}>
            Вложения чата
          </h2>
          <button
            ref={closeRef}
            type="button"
            className={styles.closeBtn}
            onClick={handleGalleryClose}
            aria-label="Закрыть"
          >
            ×
          </button>
        </div>

        <div className={styles.tabs} role="tablist">
          {TABS.map((t) => (
            <button
              key={t.kind}
              type="button"
              role="tab"
              aria-selected={tab === t.kind}
              className={tab === t.kind ? `${styles.tab} ${styles.tabActive}` : styles.tab}
              onClick={() => setTab(t.kind)}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div className={styles.body}>
          {isLoading ? (
            <p className={styles.empty}>Загрузка…</p>
          ) : isError ? (
            <p className={styles.empty}>Не удалось загрузить вложения</p>
          ) : items.length === 0 ? (
            <p className={styles.empty}>Пока нет вложений</p>
          ) : tab === 'media' ? (
            <div className={styles.mediaGrid}>
              {items.map((att) => (
                <MediaGalleryTile key={att.id} att={att} onPreview={() => setPreviewAtt(att)} />
              ))}
            </div>
          ) : (
            <div className={styles.list}>
              {items.map((att) =>
                tab === 'audio' ? (
                  <VoiceGalleryRow key={att.id} att={att} onJump={() => jump(att.message_id)} />
                ) : (
                  <FileGalleryRow key={att.id} att={att} onJump={() => jump(att.message_id)} />
                ),
              )}
            </div>
          )}
          {hasNextPage ? (
            <button
              type="button"
              className={styles.loadMoreBtn}
              disabled={isFetchingNextPage}
              onClick={() => fetchNextPage()}
            >
              {isFetchingNextPage ? 'Загрузка…' : 'Показать ещё'}
            </button>
          ) : null}
        </div>
      </div>

      {previewAtt ? (
        <MediaLightbox
          url={previewAtt.download_url}
          filename={previewAtt.original_filename}
          contentType={previewAtt.content_type}
          elevated
          onClose={() => setPreviewAtt(null)}
          footer={
            previewAtt.message_id ? (
              <button
                type="button"
                className={styles.rowLinkBtn}
                onClick={() => jump(previewAtt.message_id)}
              >
                К сообщению
              </button>
            ) : null
          }
        />
      ) : null}
    </div>
  )
}
