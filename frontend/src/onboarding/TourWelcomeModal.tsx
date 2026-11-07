import { useEffect, useId, useRef } from 'react'
import { resolveGuidedTourSkipLabel } from '../domain/onboarding/guidedTour'
import { useBodyScrollLock } from '../hooks/useBodyScrollLock'
import { useFocusTrap } from '../hooks/useFocusTrap'
import styles from '@/styles/modules/onboarding/GuidedTour.module.css'

type TourVariant = 'full' | 'timesheet'

type Props = {
  onStart: () => void
  onSkip?: () => void
  canSkipEntire?: boolean
  variant?: TourVariant
}

const WELCOME_BODY: Record<TourVariant, string> = {
  full:
    'Познакомимся с основными возможностями портала. Покажем, где искать информацию, работать с задачами, документами и другими разделами.',
  timesheet:
    'Познакомимся с таймшитами и документами для разработчиков. Обучение можно пропустить целиком или пройти по шагам.',
}

export function TourWelcomeModal({
  onStart,
  onSkip,
  canSkipEntire = false,
  variant = 'full',
}: Props) {
  const dialogRef = useRef<HTMLDivElement>(null)
  const startRef = useRef<HTMLButtonElement>(null)
  const titleId = useId()

  useBodyScrollLock()
  useFocusTrap(dialogRef)

  useEffect(() => {
    startRef.current?.focus({ preventScroll: true })
  }, [])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && canSkipEntire && onSkip) onSkip()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [canSkipEntire, onSkip])

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
          Добро пожаловать!
        </h2>
        <p className={styles.modalBody}>{WELCOME_BODY[variant]}</p>
        <p className={styles.modalBody}>
          Шаги можно переключать кнопками «Назад» / «Далее» или стрелками на клавиатуре:
          <br />← → , ↑ ↓
        </p>
        <div className={styles.modalActions}>
          {canSkipEntire && onSkip ? (
            <button type="button" className="btn-secondary" onClick={onSkip}>
              {resolveGuidedTourSkipLabel(true)}
            </button>
          ) : null}
          <button ref={startRef} type="button" className="btn-primary" onClick={onStart}>
            Начать
          </button>
        </div>
      </div>
    </div>
  )
}
