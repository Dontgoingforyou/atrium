import { useEffect, useId, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'

import { useClickOutside } from '../../hooks/useClickOutside'
import styles from '@/styles/modules/common/TimePicker.module.css'

type Props = {
  value: string
  onChange: (next: string) => void
  'aria-label'?: string
  className?: string
  invalid?: boolean
}

const HOURS = Array.from({ length: 24 }, (_, i) => String(i).padStart(2, '0'))
const MINUTES = Array.from({ length: 12 }, (_, i) => String(i * 5).padStart(2, '0'))
const POPOVER_MIN_WIDTH = 280
const VIEWPORT_PAD = 8

function parseTime(value: string): { hour: string; minute: string } {
  const [h = '10', m = '00'] = value.split(':')
  const hour = HOURS.includes(h) ? h : '10'
  const minuteNum = Number.parseInt(m, 10)
  const snapped = Number.isFinite(minuteNum)
    ? String(Math.min(55, Math.round(minuteNum / 5) * 5)).padStart(2, '0')
    : '00'
  const minute = MINUTES.includes(snapped) ? snapped : '00'
  return { hour, minute }
}

export function TimePicker({
  value,
  onChange,
  'aria-label': ariaLabel,
  className,
  invalid = false,
}: Props) {
  const parsed = parseTime(value)
  const [open, setOpen] = useState(false)
  const [pos, setPos] = useState({ top: 0, left: 0 })
  const wrapRef = useRef<HTMLDivElement>(null)
  const popoverRef = useRef<HTMLDivElement>(null)
  const listId = useId()

  useClickOutside(open, [wrapRef, popoverRef], () => setOpen(false), 'mousedown')
  useEffect(() => {
    if (!open) return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open])

  useLayoutEffect(() => {
    if (!open) return

    function recalc() {
      if (!wrapRef.current) return
      const rect = wrapRef.current.getBoundingClientRect()
      const popWidth = Math.max(POPOVER_MIN_WIDTH, popoverRef.current?.offsetWidth ?? POPOVER_MIN_WIDTH)
      // Прижимаем к правому краю триггера — поле времени обычно справа в модалке
      let left = rect.right - popWidth
      left = Math.max(VIEWPORT_PAD, Math.min(left, window.innerWidth - popWidth - VIEWPORT_PAD))
      const estimatedHeight = popoverRef.current?.offsetHeight ?? 220
      let top = rect.bottom + 6
      if (top + estimatedHeight > window.innerHeight - VIEWPORT_PAD) {
        top = Math.max(VIEWPORT_PAD, rect.top - estimatedHeight - 6)
      }
      setPos({ top, left })
    }

    recalc()
    window.addEventListener('scroll', recalc, true)
    window.addEventListener('resize', recalc)
    return () => {
      window.removeEventListener('scroll', recalc, true)
      window.removeEventListener('resize', recalc)
    }
  }, [open])

  function pickHour(hour: string) {
    onChange(`${hour}:${parsed.minute}`)
  }

  function pickMinute(minute: string) {
    onChange(`${parsed.hour}:${minute}`)
    setOpen(false)
  }

  const rootClass = [styles.root, className].filter(Boolean).join(' ')
  const display = `${parsed.hour}:${parsed.minute}`

  const popover =
    open && typeof document !== 'undefined'
      ? createPortal(
          <div
            ref={popoverRef}
            id={listId}
            className={styles.popover}
            role="dialog"
            aria-label="Выбор времени"
            style={{ top: pos.top, left: pos.left }}
          >
            <div className={styles.columns}>
              <div className={styles.column}>
                <div className={styles.columnTitle}>Часы</div>
                <div className={styles.grid}>
                  {HOURS.map((h) => (
                    <button
                      key={h}
                      type="button"
                      className={[styles.cell, h === parsed.hour ? styles.cellSelected : '']
                        .filter(Boolean)
                        .join(' ')}
                      onClick={() => pickHour(h)}
                    >
                      {h}
                    </button>
                  ))}
                </div>
              </div>
              <div className={styles.column}>
                <div className={styles.columnTitle}>Минуты</div>
                <div className={styles.gridMinutes}>
                  {MINUTES.map((m) => (
                    <button
                      key={m}
                      type="button"
                      className={[styles.cell, m === parsed.minute ? styles.cellSelected : '']
                        .filter(Boolean)
                        .join(' ')}
                      onClick={() => pickMinute(m)}
                    >
                      {m}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>,
          document.body,
        )
      : null

  return (
    <div className={rootClass} ref={wrapRef}>
      <button
        type="button"
        className={[styles.trigger, invalid ? styles.triggerInvalid : ''].filter(Boolean).join(' ')}
        aria-expanded={open}
        aria-haspopup="dialog"
        aria-controls={listId}
        aria-label={ariaLabel ?? 'Время'}
        aria-invalid={invalid || undefined}
        onClick={() => setOpen((v) => !v)}
      >
        <span className={styles.triggerValue}>{display}</span>
        <span className={styles.triggerChevron} aria-hidden>
          {open ? '▴' : '▾'}
        </span>
      </button>
      {popover}
    </div>
  )
}
