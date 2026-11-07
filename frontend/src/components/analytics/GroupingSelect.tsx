import { useEffect, useId, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useDropdownPosition } from '../../hooks/useDropdownPosition'
import { useClickOutside } from '../../hooks/useClickOutside'
import styles from '@/styles/modules/analytics/AnalyticsReportsPage.module.css'

const GROUP_BY_OPTIONS = [
  { value: 'week' as const, label: 'По неделям' },
  { value: 'month' as const, label: 'По месяцам' },
]

type GroupBy = (typeof GROUP_BY_OPTIONS)[number]['value']

type Props = {
  value: GroupBy
  onChange: (value: GroupBy) => void
}

export function GroupingSelect({ value, onChange }: Props) {
  const [open, setOpen] = useState(false)
  const [activeIndex, setActiveIndex] = useState(0)
  const triggerWrapRef = useRef<HTMLDivElement>(null)
  const triggerBtnRef = useRef<HTMLButtonElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)
  const optionRefs = useRef<Array<HTMLButtonElement | null>>([])
  const menuPos = useDropdownPosition(open, triggerWrapRef, 280, 0)

  const listboxId = useId()
  const optionIds = GROUP_BY_OPTIONS.map((_, i) => `${listboxId}-opt-${i}`)

  const selectedIndex = Math.max(
    0,
    GROUP_BY_OPTIONS.findIndex((option) => option.value === value),
  )
  const current = GROUP_BY_OPTIONS[selectedIndex]

  useClickOutside(open, [triggerWrapRef, menuRef], () => setOpen(false), 'mousedown')

  useEffect(() => {
    if (!open) return
    optionRefs.current[activeIndex]?.scrollIntoView({ block: 'nearest' })
  }, [open, activeIndex])

  useEffect(() => {
    if (!open) return
    menuRef.current?.focus()
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        e.preventDefault()
        setOpen(false)
        triggerBtnRef.current?.focus()
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open])

  function openMenu() {
    // При открытии — старт с текущего выбора (раньше синхронно в effect,
    // что вызывало каскад рендеров; теперь event-driven).
    setActiveIndex(selectedIndex)
    setOpen(true)
  }

  function toggleMenu() {
    if (open) {
      setOpen(false)
    } else {
      setActiveIndex(selectedIndex)
      setOpen(true)
    }
  }

  function pick(next: GroupBy) {
    onChange(next)
    setOpen(false)
    triggerBtnRef.current?.focus()
  }

  function onTriggerKeyDown(e: React.KeyboardEvent<HTMLButtonElement>) {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault()
      openMenu()
    }
  }

  function onListboxKeyDown(e: React.KeyboardEvent<HTMLDivElement>) {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setActiveIndex((i) => Math.min(i + 1, GROUP_BY_OPTIONS.length - 1))
        break
      case 'ArrowUp':
        e.preventDefault()
        setActiveIndex((i) => Math.max(i - 1, 0))
        break
      case 'Home':
        e.preventDefault()
        setActiveIndex(0)
        break
      case 'End':
        e.preventDefault()
        setActiveIndex(GROUP_BY_OPTIONS.length - 1)
        break
      case 'Enter':
      case ' ':
        e.preventDefault()
        pick(GROUP_BY_OPTIONS[activeIndex].value)
        break
      case 'Escape':
        e.preventDefault()
        setOpen(false)
        triggerBtnRef.current?.focus()
        break
    }
  }

  const menu = open
    ? createPortal(
        <div
          ref={menuRef}
          id={listboxId}
          className={styles.groupingMenu}
          role="listbox"
          aria-label="Группировка"
          aria-activedescendant={optionIds[activeIndex]}
          tabIndex={0}
          style={{ top: menuPos.top, left: menuPos.left, width: menuPos.width }}
          onKeyDown={onListboxKeyDown}
        >
          {GROUP_BY_OPTIONS.map((option, i) => {
            const selected = option.value === value
            const active = i === activeIndex
            return (
              <button
                key={option.value}
                ref={(el) => { optionRefs.current[i] = el }}
                id={optionIds[i]}
                type="button"
                role="option"
                tabIndex={-1}
                aria-selected={selected}
                className={`${styles.groupingMenuItem} ${active ? styles.groupingMenuItemActive : ''}`}
                onMouseEnter={() => setActiveIndex(i)}
                onClick={() => pick(option.value)}
              >
                <span className={styles.groupingMenuCheck} aria-hidden>
                  {selected ? '✓' : ''}
                </span>
                {option.label}
              </button>
            )
          })}
        </div>,
        document.body,
      )
    : null

  return (
    <>
      <div ref={triggerWrapRef} className={styles.groupingControl}>
        <span className={styles.groupingLabel}>Группировка:</span>
        <button
          ref={triggerBtnRef}
          type="button"
          className={styles.groupingTrigger}
          aria-expanded={open}
          aria-haspopup="listbox"
          aria-controls={listboxId}
          onClick={toggleMenu}
          onKeyDown={onTriggerKeyDown}
        >
          {current?.label}
          <span className={styles.groupingChevron} aria-hidden>
            ▾
          </span>
        </button>
      </div>
      {menu}
    </>
  )
}
