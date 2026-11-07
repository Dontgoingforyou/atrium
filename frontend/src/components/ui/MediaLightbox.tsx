import { useEffect, useRef, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

import { useBodyScrollLock } from '../../hooks/useBodyScrollLock'
import { useFocusTrap } from '../../hooks/useFocusTrap'
import styles from '@/styles/modules/ui/MediaLightbox.module.css'

/** Модальный предпросмотр изображения или видео (Escape/клик по фону закрывает). */
export function MediaLightbox({
  url,
  filename,
  contentType,
  onClose,
  elevated = false,
  footer,
}: {
  url: string
  filename: string
  contentType: string
  onClose: () => void
  elevated?: boolean
  footer?: ReactNode
}) {
  const overlayRef = useRef<HTMLDivElement>(null)
  const closeRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    closeRef.current?.focus()
  }, [])

  useFocusTrap(overlayRef)
  useBodyScrollLock()

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  const isVideo = contentType.startsWith('video/')

  return createPortal(
    <div
      ref={overlayRef}
      className={`${styles.lightboxOverlay}${elevated ? ` ${styles.lightboxOverlayElevated}` : ''}`}
      role="dialog"
      aria-modal="true"
      aria-label={filename}
      onClick={onClose}
    >
      <button ref={closeRef} type="button" className={styles.lightboxClose} aria-label="Закрыть" onClick={onClose}>
        ×
      </button>
      {isVideo ? (
        <video
          src={url}
          controls
          autoPlay
          className={styles.lightboxVideo}
          onClick={(e) => e.stopPropagation()}
        />
      ) : (
        <img
          src={url}
          alt={filename}
          className={styles.lightboxImage}
          onClick={(e) => e.stopPropagation()}
        />
      )}
      {footer ? (
        <div className={styles.lightboxFooter} onClick={(e) => e.stopPropagation()}>
          {footer}
        </div>
      ) : null}
    </div>,
    document.body,
  )
}
