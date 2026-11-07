import {
  type ChangeEvent,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from 'react'
import { createPortal } from 'react-dom'

import { useClickOutside } from '../../hooks/useClickOutside'
import { useDropdownPosition } from '../../hooks/useDropdownPosition'
import {
  SEARCHABLE_PICKER_PAGE_SIZE,
  labelByValue,
  type SearchablePickerOption,
} from './searchablePickerUtils'
import styles from '@/styles/modules/ui/SearchablePicker.module.css'

const DROPDOWN_MAX_HEIGHT = 280

type Props = {
  value: string
  onChange: (value: string) => void
  options: SearchablePickerOption[]
  placeholder?: string
  loading?: boolean
  /** Ошибка загрузки options — показывается в дропдауне вместо пустого списка. */
  error?: boolean
  pageSize?: number
  /** Локальная фильтрация options; false — список уже отфильтрован с сервера. */
  filterLocally?: boolean
  onQueryChange?: (query: string) => void
}

export function SearchableSinglePicker({
  value,
  onChange,
  options,
  placeholder = 'Поиск…',
  loading = false,
  error = false,
  pageSize = SEARCHABLE_PICKER_PAGE_SIZE,
  filterLocally = true,
  onQueryChange,
}: Props) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [visibleLimit, setVisibleLimit] = useState(pageSize)
  const [prevQuery, setPrevQuery] = useState(query)
  const [prevOpen, setPrevOpen] = useState(open)
  const [prevPageSize, setPrevPageSize] = useState(pageSize)
  const [activeIndex, setActiveIndex] = useState(0)

  if (prevQuery !== query || prevOpen !== open || prevPageSize !== pageSize) {
    setPrevQuery(query)
    setPrevOpen(open)
    setPrevPageSize(pageSize)
    setVisibleLimit(pageSize)
  }

  const anchorRef = useRef<HTMLDivElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const dropdownPos = useDropdownPosition(open, anchorRef, DROPDOWN_MAX_HEIGHT)
  useClickOutside(open, [anchorRef, dropdownRef], () => setOpen(false))

  const listboxId = useId()

  const selectedLabel = value ? labelByValue(options, value) : ''

  const filtered = useMemo(() => {
    if (!filterLocally) return options
    const q = query.trim().toLowerCase()
    return options.filter((opt) => {
      if (!q) return true
      return (
        opt.label.toLowerCase().includes(q) ||
        (opt.secondary?.toLowerCase().includes(q) ?? false) ||
        opt.value.toLowerCase().includes(q)
      )
    })
  }, [options, query, filterLocally])

  const visible = filtered.slice(0, visibleLimit)
  const hasMore = filtered.length > visibleLimit
  const safeActiveIndex = visible.length === 0 ? 0 : Math.min(activeIndex, visible.length - 1)

  // Скроллим клавиатурно-активный опцион в зону видимости.
  useEffect(() => {
    if (!open || visible.length === 0) return
    const el = dropdownRef.current?.querySelector<HTMLElement>(`#${CSS.escape(`${listboxId}-opt-${safeActiveIndex}`)}`)
    el?.scrollIntoView({ block: 'nearest' })
  }, [open, safeActiveIndex, listboxId, visible.length])

  useEffect(() => {
    if (!open) return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        e.preventDefault()
        setOpen(false)
        inputRef.current?.focus()
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open])

  function handleFocus() {
    setOpen(true)
    setQuery('')
    onQueryChange?.('')
  }

  function pickOption(opt: SearchablePickerOption) {
    onChange(opt.value)
    setOpen(false)
    setQuery('')
    onQueryChange?.('')
    inputRef.current?.focus()
  }

  function handleInputChange(e: ChangeEvent<HTMLInputElement>) {
    const next = e.target.value
    setOpen(true)
    setQuery(next)
    setActiveIndex(0)
    onQueryChange?.(next)
  }

  function handleInputKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!open || loading || error) return
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setOpen(true)
        setActiveIndex(visible.length === 0 ? 0 : Math.min(safeActiveIndex + 1, visible.length - 1))
        break
      case 'ArrowUp':
        e.preventDefault()
        setActiveIndex(Math.max(safeActiveIndex - 1, 0))
        break
      case 'Enter':
        if (visible[safeActiveIndex]) {
          e.preventDefault()
          pickOption(visible[safeActiveIndex])
        }
        break
      case 'Escape':
        e.preventDefault()
        setOpen(false)
        break
    }
  }

  const displayValue = open ? query : selectedLabel

  const dropdownPortal = open
    ? createPortal(
        <div
          ref={dropdownRef}
          id={listboxId}
          className={styles.dropdown}
          role="listbox"
          aria-label={placeholder}
          style={{
            top: dropdownPos.top,
            left: dropdownPos.left,
            width: dropdownPos.width,
            maxHeight: dropdownPos.maxHeight,
          }}
        >
          {loading ? (
            <p className={styles.emptyHint}>Загрузка…</p>
          ) : error ? (
            <p className={styles.emptyHint} role="alert">
              Ошибка загрузки списка
            </p>
          ) : visible.length > 0 ? (
            <>
              {visible.map((opt, i) => {
                const active = i === safeActiveIndex
                return (
                  <div
                    key={opt.value}
                    id={`${listboxId}-opt-${i}`}
                    className={styles.option}
                    role="option"
                    aria-selected={opt.value === value}
                    onMouseDown={(e) => {
                      e.preventDefault()
                      pickOption(opt)
                    }}
                    onMouseEnter={() => setActiveIndex(i)}
                    data-active={active || undefined}
                  >
                    <div className={styles.optionText}>
                      <span className={styles.optionName}>{opt.label}</span>
                      {opt.secondary && opt.secondary !== opt.label ? (
                        <span className={styles.optionSecondary}>{opt.secondary}</span>
                      ) : null}
                    </div>
                  </div>
                )
              })}
              {hasMore ? (
                <button
                  type="button"
                  className={styles.loadMore}
                  onMouseDown={(e) => {
                    e.preventDefault()
                    setVisibleLimit((n) => n + pageSize)
                  }}
                >
                  Ещё ({filtered.length - visibleLimit})
                </button>
              ) : null}
            </>
          ) : (
            <p className={styles.emptyHint}>Нет совпадений — измените запрос</p>
          )}
        </div>,
        document.body,
      )
    : null

  return (
    <div ref={anchorRef} className={styles.wrapper}>
      <div className={styles.inputRow}>
        <input
          ref={inputRef}
          type="text"
          className={`form-input filter-select ${styles.input}`}
          role="combobox"
          aria-expanded={open}
          aria-controls={listboxId}
          aria-autocomplete="list"
          aria-activedescendant={open && visible[safeActiveIndex] ? `${listboxId}-opt-${safeActiveIndex}` : undefined}
          aria-label={placeholder}
          placeholder={placeholder}
          value={displayValue}
          onChange={handleInputChange}
          onFocus={handleFocus}
          onClick={() => {
            if (!open) setOpen(true)
          }}
          onKeyDown={handleInputKeyDown}
        />
      </div>
      {dropdownPortal}
    </div>
  )
}
