import { forwardRef, useId } from 'react'

import { resolveGuidedTourSkipLabel } from '../domain/onboarding/guidedTour'
import styles from '@/styles/modules/onboarding/GuidedTour.module.css'

type Props = {
  title: string
  body: string
  progressLabel: string
  style: { top: number; left: number }
  contentKey: string
  visible: boolean
  canBack: boolean
  onBack: () => void
  onNext: () => void
  onSkip: () => void
  showSkip?: boolean
  canSkipEntire?: boolean
  skipLabel?: string
  isLast: boolean
}

export const TourPopover = forwardRef<HTMLDivElement, Props>(function TourPopover(
  {
    title,
    body,
    progressLabel,
    style,
    contentKey,
    visible,
    canBack,
    onBack,
    onNext,
    onSkip,
    showSkip = true,
    canSkipEntire = false,
    skipLabel,
    isLast,
  },
  ref,
) {
  const titleId = useId()
  return (
    <div
      ref={ref}
      className={`${styles.popover} ${visible ? styles.popoverVisible : styles.popoverHidden}`}
      style={style}
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      aria-hidden={!visible}
    >
      <div key={contentKey} className={styles.popoverContent}>
        <div className={styles.popoverScroll}>
          <h2 id={titleId} className={styles.popoverTitle}>
            {title}
          </h2>
          <p className={styles.popoverBody}>{body}</p>
          <p className={styles.popoverProgress}>{progressLabel}</p>
          <p className={styles.popoverHint}>Стрелки ← → (или ↑ ↓) — предыдущий / следующий шаг</p>
        </div>
        <div className={styles.popoverActions}>
          {showSkip ? (
            <button type="button" className="btn-secondary" onClick={onSkip}>
              {skipLabel ?? resolveGuidedTourSkipLabel(canSkipEntire)}
            </button>
          ) : null}
          <span className={styles.popoverActionsSpacer} />
          <button type="button" className="btn-secondary" onClick={onBack} disabled={!canBack}>
            Назад
          </button>
          <button type="button" className="btn-primary" onClick={onNext}>
            {isLast ? 'Готово' : 'Далее'}
          </button>
        </div>
      </div>
    </div>
  )
})
