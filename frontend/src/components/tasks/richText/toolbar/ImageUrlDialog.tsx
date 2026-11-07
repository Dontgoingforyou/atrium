import { useState } from 'react'
import { Modal } from '@/components/ui/Modal'
import styles from '@/styles/modules/tasks/RichTextEditorDialogs.module.css'

type Props = {
  open: boolean
  onClose: () => void
  onInsert: (url: string) => void
}

function isAllowedImageUrl(raw: string): boolean {
  try {
    const u = new URL(raw.trim())
    return u.protocol === 'https:'
  } catch {
    return false
  }
}

// Оборачиваем содержимое: компонент монтируется только при open=true,
// поэтому state всегда инициализируется свежим при открытии диалога.
export function ImageUrlDialog({ open, ...rest }: Props) {
  if (!open) return null
  return <ImageUrlDialogContent {...rest} />
}

function ImageUrlDialogContent({ onClose, onInsert }: Omit<Props, 'open'>) {
  const [url, setUrl] = useState('')
  const [error, setError] = useState('')

  const previewOk = isAllowedImageUrl(url)

  function handleInsert() {
    if (!isAllowedImageUrl(url)) {
      setError('Укажите ссылку на изображение (только HTTPS)')
      return
    }
    onInsert(url.trim())
    onClose()
  }

  return (
    <Modal title="Вставить изображение по ссылке" onClose={onClose} maxWidth={420}>
      <p className={styles.dialogHint}>
        Вставьте прямую HTTPS-ссылку на файл изображения.
      </p>
      <input
        type="url"
        className={styles.dialogInput}
        placeholder="https://example.com/image.png"
        value={url}
        onChange={(e) => {
          setUrl(e.target.value)
          setError('')
        }}
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            e.preventDefault()
            handleInsert()
          }
        }}
      />
      {error ? <p className={styles.dialogError}>{error}</p> : null}
      {previewOk ? (
        <img
          src={url.trim()}
          alt="Предпросмотр изображения"
          className={styles.dialogPreview}
        />
      ) : null}
      <div className={styles.dialogActions}>
        <button type="button" className={styles.dialogBtnSecondary} onClick={onClose}>
          Отмена
        </button>
        <button type="button" className={styles.dialogBtnPrimary} onClick={handleInsert}>
          Вставить
        </button>
      </div>
    </Modal>
  )
}
