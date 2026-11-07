import { useEffect, useId, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useClickOutside } from '../../hooks/useClickOutside'
import { useDropdownPosition } from '../../hooks/useDropdownPosition'
import {
  buildMonthDayGrid,
  dateStrToView,
  formatDayCalendarLabel,
  formatMonthYearTitle,
  isDateDisabled,
  todayDateStr,
} from '../../utils/calendar/dayCalendarUtils'
import styles from '@/styles/modules/common/DayCalendarPicker.module.css'

const WEEKDAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
const DAY_POPOVER_MAX_HEIGHT = 420
const DAY_POPOVER_MIN_WIDTH = 320

type Props = {
  value: string
  label: string
  onChange: (next: string) => void
  minDate?: string
  maxDate?: string
  placeholder?: string
  className?: string
  allowClear?: boolean
  invalid?: boolean
}

/** Выбор даты через всплывающий календарь с сеткой дней. */
export function DayCalendarPicker({
  value,
  label,
  onChange,
  minDate,
  maxDate,
  placeholder = 'Не выбрано',
  className,
  allowClear = true,
  invalid = false,
}: Props) {
  const parsed = dateStrToView(value)
  const [open, setOpen] = useState(false)
  const [viewYear, setViewYear] = useState(parsed.year)
  const [viewMonthIndex, setViewMonthIndex] = useState(parsed.monthIndex)
  const wrapRef = useRef<HTMLDivElement>(null)
  const popoverRef = useRef<HTMLDivElement>(null)
  const listId = useId()
  const today = todayDateStr()
  const pos = useDropdownPosition(open, wrapRef, DAY_POPOVER_MAX_HEIGHT, DAY_POPOVER_MIN_WIDTH)

  useClickOutside(open, [wrapRef, popoverRef], () => setOpen(false), 'mousedown')
  useEffect(() => {
    if (!open) return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open])

  function toggleOpen() {
    if (!open) {
      const v = dateStrToView(value)
      setViewYear(v.year)
      setViewMonthIndex(v.monthIndex)
    }
    setOpen(!open)
  }

  function shiftMonth(delta: number) {
    const d = new Date(viewYear, viewMonthIndex + delta, 1)
    setViewYear(d.getFullYear())
    setViewMonthIndex(d.getMonth())
  }

  function pick(dateStr: string) {
    if (isDateDisabled(dateStr, minDate, maxDate)) return
    onChange(dateStr)
    setOpen(false)
  }

  function clear() {
    onChange('')
    setOpen(false)
  }

  const displayValue = value ? formatDayCalendarLabel(value) : placeholder
  const rootClass = [styles.root, className].filter(Boolean).join(' ')
  const cells = buildMonthDayGrid(viewYear, viewMonthIndex)
  const showClear = allowClear && Boolean(value)

  const popover =
    open && typeof document !== 'undefined'
      ? createPortal(
          <div
            ref={popoverRef}
            id={listId}
            className={styles.popover}
            role="dialog"
            aria-label="Выбор даты"
            data-portal-dropdown="calendar-picker"
            style={{
              top: pos.top,
              left: pos.left,
              width: pos.width,
              maxHeight: pos.maxHeight,
            }}
          >
          <div className={styles.monthRow}>
            <button
              type="button"
              className={styles.monthNav}
              aria-label="Предыдущий месяц"
              onClick={() => shiftMonth(-1)}
            >
              ‹
            </button>
            <span className={styles.monthTitle}>
              {formatMonthYearTitle(viewYear, viewMonthIndex)}
            </span>
            <button
              type="button"
              className={styles.monthNav}
              aria-label="Следующий месяц"
              onClick={() => shiftMonth(1)}
            >
              ›
            </button>
          </div>

          <div className={styles.weekdayRow}>
            {WEEKDAYS.map((wd) => (
              <span key={wd} className={styles.weekday}>{wd}</span>
            ))}
          </div>

          <div className={styles.dayGrid}>
            {cells.map((cell) => {
              const selected = value === cell.dateStr
              const disabled = isDateDisabled(cell.dateStr, minDate, maxDate)
              const isToday = cell.dateStr === today
              return (
                <button
                  key={cell.dateStr}
                  type="button"
                  className={[
                    styles.dayBtn,
                    cell.outsideMonth ? styles.dayBtnOutside : '',
                    isToday ? styles.dayBtnToday : '',
                    selected ? styles.dayBtnSelected : '',
                    disabled ? styles.dayBtnDisabled : '',
                  ].filter(Boolean).join(' ')}
                  disabled={disabled}
                  onClick={() => pick(cell.dateStr)}
                >
                  {cell.day}
                </button>
              )
            })}
          </div>

          {showClear ? (
            <div className={styles.clearRow}>
              <button type="button" className={styles.clearBtn} onClick={clear}>
                Очистить
              </button>
            </div>
          ) : null}
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
        aria-invalid={invalid || undefined}
        onClick={toggleOpen}
      >
        <span className={styles.triggerLabel}>{label}</span>
        <span
          className={[
            styles.triggerValue,
            !value ? styles.triggerValueEmpty : '',
            invalid && value ? styles.triggerValueInvalid : '',
          ].filter(Boolean).join(' ')}
        >
          {displayValue}
        </span>
        <span className={styles.triggerChevron} aria-hidden>
          {open ? '▴' : '▾'}
        </span>
      </button>
      {popover}
    </div>
  )
}
