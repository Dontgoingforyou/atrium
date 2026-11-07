import { type ReactNode, useCallback, useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useBodyScrollLock } from '../../hooks/useBodyScrollLock'
import { useFocusTrap } from '../../hooks/useFocusTrap'
import styles from '@/styles/modules/ui/Modal.module.css'

// Длительность CSS-анимации закрытия (.dialogClosing/.overlayClosing) — сколько
// ждём перед фактическим размонтированием через onClose().
const CLOSE_ANIMATION_MS = 150
// Скрываем «удержание» фона первые мгновения после маунта, чтобы клик по триггеру,
// «накрывший» открывшуюся модалку, не закрыл её тут же (компенсация всплытия mousedown).
const BACKDROP_IGNORE_MS = 400

type Props = {
  /** Заголовок модалки (необязателен). */
  title?: string
  /** Ширина контентной части, по умолчанию 560px. */
  maxWidth?: number | string
  onClose: () => void
  children: ReactNode
  closeOnBackdrop?: boolean
}

export function Modal({
  title,
  maxWidth = 560,
  onClose,
  children,
  closeOnBackdrop = true,
}: Props) {
  const dialogRef = useRef<HTMLDivElement>(null)
  const closeRef = useRef<HTMLButtonElement>(null)
  const overlayPointerDownRef = useRef(false)
  const backdropIgnoreUntilRef = useRef(0)
  const closeTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [isClosing, setIsClosing] = useState(false)

  const handleClose = useCallback(() => {
    setIsClosing(true)
    closeTimeoutRef.current = setTimeout(() => onClose(), CLOSE_ANIMATION_MS)
  }, [onClose])

  useEffect(() => {
    return () => {
      if (closeTimeoutRef.current !== null) clearTimeout(closeTimeoutRef.current)
    }
  }, [])

  const handleOverlayMouseDown = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (!closeOnBackdrop) return
      if (Date.now() < backdropIgnoreUntilRef.current) return
      overlayPointerDownRef.current = e.target === e.currentTarget
    },
    [closeOnBackdrop],
  )

  const handleOverlayMouseUp = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (!closeOnBackdrop) return
      if (Date.now() < backdropIgnoreUntilRef.current) {
        overlayPointerDownRef.current = false
        return
      }
      const selection = window.getSelection()?.toString()
      if (selection && selection.length > 0) {
        overlayPointerDownRef.current = false
        return
      }
      if (overlayPointerDownRef.current && e.target === e.currentTarget) {
        handleClose()
      }
      overlayPointerDownRef.current = false
    },
    [closeOnBackdrop, handleClose],
  )

  useEffect(() => {
    backdropIgnoreUntilRef.current = Date.now() + BACKDROP_IGNORE_MS
    closeRef.current?.focus({ preventScroll: true })
  }, [])

  useBodyScrollLock()
  useFocusTrap(dialogRef)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') handleClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [handleClose])

  return createPortal(
    <div
      className={`${styles.overlay}${isClosing ? ` ${styles.overlayClosing}` : ''}`}
      role="presentation"
      onMouseDown={handleOverlayMouseDown}
      onMouseUp={handleOverlayMouseUp}
    >
      <div
        ref={dialogRef}
        className={`${styles.dialog}${isClosing ? ` ${styles.dialogClosing}` : ''}`}
        role="dialog"
        aria-modal="true"
        aria-label={title ?? 'Диалог'}
        style={{ maxWidth }}
        onMouseDown={(e) => e.stopPropagation()}
        onMouseUp={(e) => e.stopPropagation()}
        onClick={(e) => e.stopPropagation()}
      >
        <div className={styles.header}>
          {title ? <h2 className={styles.title}>{title}</h2> : <span />}
          <button
            ref={closeRef}
            type="button"
            className={styles.closeBtn}
            aria-label="Закрыть"
            onClick={handleClose}
          >
            ✕
          </button>
        </div>
        <div className={styles.body}>{children}</div>
      </div>
    </div>,
    document.body,
  )
}
