import { useEffect, useId, useRef, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { useBodyScrollLock } from '../../hooks/useBodyScrollLock'
import { useFocusTrap } from '../../hooks/useFocusTrap'
import { playUiSound } from '../../utils/sound/uiSounds'
import styles from '@/styles/modules/ui/ConfirmDialog.module.css'

type Props = {
  open: boolean
  title: string
  message?: string
  children?: ReactNode
  confirmLabel?: string
  cancelLabel?: string
  discardLabel?: string
  /** Красная кнопка подтверждения для деструктивных действий. */
  destructive?: boolean
  /** Смысловой звук на подтверждении (не tap). Повторный error в onError мутации не нужен. */
  confirmSound?: 'error'
  disabled?: boolean
  onConfirm: () => void
  onCancel: () => void
  onDiscard?: () => void
}

export function ConfirmDialog({
  open,
  title,
  message,
  children,
  confirmLabel = 'Подтвердить',
  cancelLabel = 'Отмена',
  discardLabel,
  destructive = false,
  confirmSound,
  disabled = false,
  onConfirm,
  onCancel,
  onDiscard,
}: Props) {
  const dialogRef = useRef<HTMLDivElement>(null)
  const cancelRef = useRef<HTMLButtonElement>(null)
  const titleId = useId()
  const msgId = useId()

  useEffect(() => {
    if (open) cancelRef.current?.focus()
  }, [open])

  useFocusTrap(dialogRef, open)
  useBodyScrollLock(open)

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCancel()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onCancel])

  if (!open) return null

  return createPortal(
    <div
      className={styles.overlay}
      role="presentation"
      onClick={() => onCancel()}
    >
      <div
        ref={dialogRef}
        className={styles.dialog}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={message ? msgId : undefined}
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id={titleId} className={styles.title}>
          {title}
        </h2>
        {message && (
          <p id={msgId} className={styles.message}>
            {message}
          </p>
        )}
        {children}
        <div className={onDiscard ? styles.actionsTriple : styles.actions}>
          <button
            ref={cancelRef}
            type="button"
            className={styles.cancelBtn}
            disabled={disabled}
            onClick={onCancel}
          >
            {cancelLabel}
          </button>
          {onDiscard && discardLabel ? (
            <button
              type="button"
              className={styles.discardBtn}
              disabled={disabled}
              onClick={onDiscard}
            >
              {discardLabel}
            </button>
          ) : null}
          <button
            type="button"
            className={`${styles.confirmBtn}${destructive ? ` ${styles.destructive}` : ''}`}
            disabled={disabled}
            onClick={() => {
              if (confirmSound === 'error') {
                playUiSound('error')
              }
              onConfirm()
            }}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  )
}
