import { useState } from 'react'
import { normalizeHttpUrl } from '@/utils/html/normalizeHttpUrl'
import { Modal } from '@/components/ui/Modal'
import styles from '@/styles/modules/tasks/RichTextEditorDialogs.module.css'

type Props = {
  open: boolean
  initialUrl: string
  onClose: () => void
  onApply: (url: string) => void
  onRemove: () => void
}

// Оборачиваем содержимое: компонент монтируется только при open=true,
// поэтому state всегда инициализируется свежим при открытии диалога.
export function LinkDialog({ open, ...rest }: Props) {
  if (!open) return null
  return <LinkDialogContent {...rest} />
}

function LinkDialogContent({
  initialUrl,
  onClose,
  onApply,
  onRemove,
}: Omit<Props, 'open'>) {
  const [url, setUrl] = useState(initialUrl)
  const [error, setError] = useState('')

  function handleApply() {
    if (!url.trim()) {
      onRemove()
      onClose()
      return
    }
    const normalized = normalizeHttpUrl(url)
    if (normalized === null) {
      setError('Укажите корректный адрес (http или https)')
      return
    }
    onApply(normalized)
    onClose()
  }

  return (
    <Modal title="Ссылка" onClose={onClose} maxWidth={420}>
      <p className={styles.dialogHint}>
        Выделите текст в редакторе, затем укажите адрес. Пустое поле — убрать ссылку с выделения.
      </p>
      <input
        type="text"
        className={styles.dialogInput}
        placeholder="https://example.com"
        value={url}
        onChange={(e) => {
          setUrl(e.target.value)
          setError('')
        }}
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            e.preventDefault()
            handleApply()
          }
        }}
      />
      {error ? <p className={styles.dialogError}>{error}</p> : null}
      <div className={styles.dialogActions}>
        {initialUrl ? (
          <button
            type="button"
            className={styles.dialogBtnSecondary}
            onClick={() => {
              onRemove()
              onClose()
            }}
          >
            Убрать ссылку
          </button>
        ) : null}
        <button type="button" className={styles.dialogBtnSecondary} onClick={onClose}>
          Отмена
        </button>
        <button type="button" className={styles.dialogBtnPrimary} onClick={handleApply}>
          Применить
        </button>
      </div>
    </Modal>
  )
}
