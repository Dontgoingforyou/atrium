import { type ReactNode, useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import { useBodyScrollLock } from '../../hooks/useBodyScrollLock'
import { useFocusTrap } from '../../hooks/useFocusTrap'
import styles from '@/styles/modules/ui/RightDrawer.module.css'

type Props = {
  /** Доступное имя диалога (aria-label). */
  ariaLabel: string
  /** Видимый заголовок в шапке drawer. */
  title: string
  entered: boolean
  onClose: () => void
  onTransitionEnd: (e: React.TransitionEvent<HTMLElement>) => void
  children: ReactNode
}

/** Правый drawer: portal + backdrop + transition + фокус на кнопке закрытия и focus trap. */
export function RightDrawer({ ariaLabel, title, entered, onClose, onTransitionEnd, children }: Props) {
  const asideRef = useRef<HTMLElement>(null)
  const closeBtnRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    closeBtnRef.current?.focus()
  }, [])

  useFocusTrap(asideRef)
  useBodyScrollLock()

  return createPortal(
    <div
      className={`${styles.backdrop} ${entered ? styles.backdropOpen : ''}`}
      role="presentation"
      onClick={onClose}
    >
      <aside
        ref={asideRef}
        className={`${styles.drawer} ${entered ? styles.drawerOpen : ''}`}
        role="dialog"
        aria-label={ariaLabel}
        aria-modal="true"
        onClick={(e) => e.stopPropagation()}
        onTransitionEnd={onTransitionEnd}
      >
        <div className={styles.head}>
          <h2 className={styles.title}>{title}</h2>
          <button type="button" ref={closeBtnRef} className={styles.close} onClick={onClose}>
            Закрыть
          </button>
        </div>
        <div className={styles.body}>{children}</div>
      </aside>
    </div>,
    document.body,
  )
}
