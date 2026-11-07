import { useEffect, useId, useRef } from 'react'
import { useBodyScrollLock } from '../hooks/useBodyScrollLock'
import { useFocusTrap } from '../hooks/useFocusTrap'
import styles from '@/styles/modules/onboarding/GuidedTour.module.css'

type TourVariant = 'full' | 'timesheet'

type Props = {
  onFinish: () => void
  variant?: TourVariant
}

const DONE_BODY: Record<TourVariant, string> = {
  full:
    'Вы познакомились с основными возможностями портала. Обучение можно пройти повторно в настройках аккаунта.',
  timesheet:
    'Вы познакомились с таймшитами и документами. Обучение можно пройти повторно кнопкой «Обучение» в левом меню.',
}

export function TourDoneModal({ onFinish, variant = 'full' }: Props) {
  const dialogRef = useRef<HTMLDivElement>(null)
  const finishRef = useRef<HTMLButtonElement>(null)
  const titleId = useId()

  useBodyScrollLock()
  useFocusTrap(dialogRef)

  useEffect(() => {
    finishRef.current?.focus({ preventScroll: true })
  }, [])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onFinish()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onFinish])

  return (
    <div className={styles.modalBackdrop} role="presentation">
      <div
        ref={dialogRef}
        className={styles.modalCard}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <h2 id={titleId} className={styles.modalTitle}>
          Готово!
        </h2>
        <p className={styles.modalBody}>{DONE_BODY[variant]}</p>
        <div className={styles.modalActions}>
          <button ref={finishRef} type="button" className="btn-primary" onClick={onFinish}>
            Приступить к работе
          </button>
        </div>
      </div>
    </div>
  )
}
