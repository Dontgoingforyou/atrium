import type { ChatAttachment } from '../../../types/chat'
import { fileChipIcon, formatBytes } from '../../../utils/fileUtils'
import styles from '@/styles/modules/chat/MessageInput.module.css'

export type PendingAttachment = {
  id: string
  file: File
  uploading: boolean
  /** Доля загруженного (0–1); undefined — прогресс браузером не сообщается (lengthComputable=false). */
  progress?: number
  error: string | null
  result: ChatAttachment | null
}

type Props = {
  items: PendingAttachment[]
  onRemove: (id: string) => void
}

export function AttachmentChipList({ items, onRemove }: Props) {
  if (items.length === 0) return null
  return (
    <div className={styles.attachmentList}>
      {items.map((item) => (
        <div key={item.id} className={styles.attachmentChip}>
          <span className={styles.attachmentIcon} aria-hidden>
            {fileChipIcon(item.file)}
          </span>
          <span className={styles.attachmentName} title={item.file.name}>
            {item.file.name}
          </span>
          <span className={styles.attachmentSize}>{formatBytes(item.file.size)}</span>
          {item.uploading && (
            <span className={styles.attachmentStatus} aria-live="polite">
              {item.progress !== undefined ? `${Math.round(item.progress * 100)}%` : 'загрузка…'}
            </span>
          )}
          {item.uploading && (
            <span className={styles.attachmentProgressTrack} aria-hidden>
              <span
                className={styles.attachmentProgressFill}
                style={{ width: `${Math.round((item.progress ?? 0) * 100)}%` }}
              />
            </span>
          )}
          {item.error && (
            <span className={`${styles.attachmentStatus} ${styles.attachmentError}`} title={item.error}>
              ошибка
            </span>
          )}
          {!item.uploading && !item.error && (
            <span className={`${styles.attachmentStatus} ${styles.attachmentDone}`}>✓</span>
          )}
          <button
            type="button"
            className={styles.attachmentRemove}
            aria-label="Удалить вложение"
            onClick={() => onRemove(item.id)}
          >
            ×
          </button>
        </div>
      ))}
    </div>
  )
}
