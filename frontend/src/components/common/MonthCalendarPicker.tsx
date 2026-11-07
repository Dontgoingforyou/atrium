import { useEffect, useId, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useClickOutside } from '../../hooks/useClickOutside'
import { useDropdownPosition } from '../../hooks/useDropdownPosition'
import {
  MONTHS_SHORT,
  formatMonthCalendarLabel,
  isMonthDisabled,
  type MonthCalendarValue,
  YEAR_PAGE_SIZE,
  yearPageStart,
  yearsInPage,
} from '../../utils/calendar/monthCalendarUtils'
import styles from '@/styles/modules/common/MonthCalendarPicker.module.css'

const CALENDAR_POPOVER_MAX_HEIGHT = 360
const CALENDAR_POPOVER_MIN_WIDTH = 280

type PickerMode = 'months' | 'years'

type Props = {
  value: MonthCalendarValue
  label: string
  onChange: (next: MonthCalendarValue) => void
  maxMonth?: string
  minMonth?: string
  className?: string
}

/** Выбор месяца через всплывающую сетку (календарь), без стрелок вбок. */
export function MonthCalendarPicker({
  value,
  label,
  onChange,
  maxMonth,
  minMonth,
  className,
}: Props) {
  const [open, setOpen] = useState(false)
  const [mode, setMode] = useState<PickerMode>('months')
  const [viewYear, setViewYear] = useState(value.year)
  const [yearPage, setYearPage] = useState(() => yearPageStart(value.year))
  const wrapRef = useRef<HTMLDivElement>(null)
  const popoverRef = useRef<HTMLDivElement>(null)
  const listId = useId()
  const pos = useDropdownPosition(
    open,
    wrapRef,
    CALENDAR_POPOVER_MAX_HEIGHT,
    CALENDAR_POPOVER_MIN_WIDTH,
  )

  function closePicker() {
    setOpen(false)
    setMode('months')
  }

  useClickOutside(open, [wrapRef, popoverRef], closePicker, 'mousedown')
  useEffect(() => {
    if (!open) return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') closePicker()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open])

  function toggleOpen() {
    if (!open) {
      setViewYear(value.year)
      setYearPage(yearPageStart(value.year))
      setMode('months')
      setOpen(true)
      return
    }
    closePicker()
  }

  function pickMonth(monthIndex: number) {
    if (isMonthDisabled(viewYear, monthIndex, minMonth, maxMonth)) return
    onChange({ year: viewYear, monthIndex })
    closePicker()
  }

  function pickYear(year: number) {
    setViewYear(year)
    setMode('months')
  }

  function openYearMode() {
    setYearPage(yearPageStart(viewYear))
    setMode('years')
  }

  const rootClass = [styles.root, className].filter(Boolean).join(' ')
  const pageYears = yearsInPage(yearPage)
  const yearRangeLabel = `${pageYears[0]}–${pageYears[pageYears.length - 1]}`

  const popover =
    open && typeof document !== 'undefined'
      ? createPortal(
          <div
            ref={popoverRef}
            id={listId}
            className={styles.popover}
            role="dialog"
            aria-label={mode === 'years' ? 'Выбор года' : 'Выбор месяца'}
            data-portal-dropdown="calendar-picker"
            style={{
              top: pos.top,
              left: pos.left,
              width: pos.width,
              maxHeight: pos.maxHeight,
            }}
          >
            <div className={styles.yearRow}>
              <button
                type="button"
                className={styles.yearNav}
                aria-label={mode === 'years' ? 'Предыдущие годы' : 'Предыдущий год'}
                onClick={() => {
                  if (mode === 'years') {
                    setYearPage((p) => p - YEAR_PAGE_SIZE)
                  } else {
                    setViewYear((y) => y - 1)
                  }
                }}
              >
                ‹
              </button>
              {mode === 'months' ? (
                <button
                  type="button"
                  className={styles.yearTitleBtn}
                  aria-label="Выбор года"
                  onClick={openYearMode}
                >
                  {viewYear}
                </button>
              ) : (
                <span className={styles.yearTitle}>{yearRangeLabel}</span>
              )}
              <button
                type="button"
                className={styles.yearNav}
                aria-label={mode === 'years' ? 'Следующие годы' : 'Следующий год'}
                onClick={() => {
                  if (mode === 'years') {
                    setYearPage((p) => p + YEAR_PAGE_SIZE)
                  } else {
                    setViewYear((y) => y + 1)
                  }
                }}
              >
                ›
              </button>
            </div>
            {mode === 'months' ? (
              <div className={styles.monthGrid}>
                {MONTHS_SHORT.map((short, monthIndex) => {
                  const selected = value.year === viewYear && value.monthIndex === monthIndex
                  const disabled = isMonthDisabled(viewYear, monthIndex, minMonth, maxMonth)
                  return (
                    <button
                      key={short}
                      type="button"
                      className={[
                        styles.monthBtn,
                        selected ? styles.monthBtnSelected : '',
                        disabled ? styles.monthBtnDisabled : '',
                      ]
                        .filter(Boolean)
                        .join(' ')}
                      disabled={disabled}
                      onClick={() => pickMonth(monthIndex)}
                    >
                      {short}
                    </button>
                  )
                })}
              </div>
            ) : (
              <div className={styles.yearGrid}>
                {pageYears.map((year) => {
                  const selected = value.year === year
                  return (
                    <button
                      key={year}
                      type="button"
                      className={[
                        styles.yearBtn,
                        selected ? styles.yearBtnSelected : '',
                      ]
                        .filter(Boolean)
                        .join(' ')}
                      onClick={() => pickYear(year)}
                    >
                      {year}
                    </button>
                  )
                })}
              </div>
            )}
          </div>,
          document.body,
        )
      : null

  return (
    <div className={rootClass} ref={wrapRef}>
      <button
        type="button"
        className={styles.trigger}
        aria-expanded={open}
        aria-haspopup="dialog"
        aria-controls={listId}
        aria-label={label || 'Выбор месяца'}
        onClick={toggleOpen}
      >
        <span className={styles.triggerLabel}>{label}</span>
        <span className={styles.triggerValue}>{formatMonthCalendarLabel(value)}</span>
        <span className={styles.triggerChevron} aria-hidden>
          {open ? '▴' : '▾'}
        </span>
      </button>
      {popover}
    </div>
  )
}
