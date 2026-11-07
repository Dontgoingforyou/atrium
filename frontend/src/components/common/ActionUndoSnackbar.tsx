import type { CSSProperties } from 'react'
import { createPortal } from 'react-dom'

import styles from '@/styles/modules/common/ActionUndoSnackbar.module.css'

type StackItem = {
  id: string
  message: string
  canUndo?: boolean
  actionLabel?: string
}

type StackProps = {
  items: StackItem[]
  onUndo: (id: string) => void
  onAction: (id: string) => void
}

const STACK_OFFSET_Y = 14
const STACK_OFFSET_X = 10
const CARD_BASE_HEIGHT = 88

/** Стек snackbar'ов undo: видны «карты» сзади, счётчик на верхней. */
export function ActionUndoSnackbarStack({ items, onUndo, onAction }: StackProps) {
  if (items.length === 0) return null

  const stackDepth = items.length - 1
  const stackHeight = CARD_BASE_HEIGHT + stackDepth * STACK_OFFSET_Y
  const front = items[items.length - 1]

  return createPortal(
    <div
      className={styles.stack}
      role="status"
      aria-live="polite"
      aria-label={
        items.length > 1
          ? `Уведомления: ${items.length}, верхнее — ${front.message}`
          : front.message
      }
      style={{ height: stackHeight }}
    >
      {items.map((item, index) => {
        const depthFromFront = items.length - 1 - index
        const isFront = depthFromFront === 0
        return (
          <div
            key={item.id}
            className={styles.cardShell}
            style={{
              '--stack-index': index,
              transform: `translate(${-depthFromFront * STACK_OFFSET_X}px, ${-depthFromFront * STACK_OFFSET_Y}px) scale(${1 - depthFromFront * 0.03})`,
              opacity: 1 - depthFromFront * 0.14,
            } as CSSProperties}
          >
            <div
              className={[styles.card, isFront ? styles.cardFront : styles.cardBehind]
                .filter(Boolean)
                .join(' ')}
            >
              {isFront && items.length > 1 ? (
                <span className={styles.countBadge} aria-hidden>
                  {items.length}
                </span>
              ) : null}
              <span className={styles.message}>{item.message}</span>
              {isFront ? (
                <>
                  {items.length > 1 ? (
                    <span className={styles.queueHint}>
                      Ещё {items.length - 1} в очереди
                    </span>
                  ) : null}
                  {item.canUndo !== false ? (
                    <button type="button" className={styles.undoBtn} onClick={() => onUndo(item.id)}>
                      Отменить
                    </button>
                  ) : item.actionLabel ? (
                    <button type="button" className={styles.undoBtn} onClick={() => onAction(item.id)}>
                      {item.actionLabel}
                    </button>
                  ) : null}
                </>
              ) : null}
            </div>
          </div>
        )
      })}
    </div>,
    document.body,
  )
}
