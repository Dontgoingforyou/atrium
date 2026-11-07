import {
  type ChangeEvent,
  type ReactNode,
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
  filterPickerOptions,
  labelByValue,
  paginateItems,
  type SearchablePickerOption,
} from './searchablePickerUtils'
import styles from '@/styles/modules/ui/SearchablePicker.module.css'

const DROPDOWN_MAX_HEIGHT = 280

/** A11y-атрибуты опции, которые кастомный renderOption обязан применить к корневому элементу опции. */
export type OptionA11yProps = {
  id: string
  role: 'option'
  'aria-selected': boolean
  'data-active': true | undefined
  onMouseEnter: () => void
}

type Props = {
  value: string[]
  onChange: (value: string[]) => void
  options: SearchablePickerOption[]
  placeholder?: string
  loading?: boolean
  /** Ошибка загрузки options — показывается в дропдауне вместо пустого списка. */
  error?: boolean
  pageSize?: number
  minDropdownWidth?: number
  renderOption?: (opt: SearchablePickerOption, pick: () => void, a11y: OptionA11yProps) => ReactNode
  chipsAriaLabel?: string
  hideChips?: boolean
  /** 'below' (по умолчанию) — чипы под полем ввода; 'right' — чипы справа от поля ввода */
  chipsPosition?: 'below' | 'right'
  /** Значения, которые нельзя снять с выбора */
  lockedValues?: string[]
  /** Просмотр: все выбранные чипы без поиска и снятия. */
  readOnly?: boolean
}

export function SearchableMultiPicker({
  value,
  onChange,
  options,
  placeholder = 'Поиск…',
  loading = false,
  error = false,
  pageSize = SEARCHABLE_PICKER_PAGE_SIZE,
  minDropdownWidth,
  renderOption,
  chipsAriaLabel = 'Выбранные значения',
  hideChips = false,
  chipsPosition = 'below',
  lockedValues = [],
  readOnly = false,
}: Props) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [visibleLimit, setVisibleLimit] = useState(pageSize)
  const [chipVisibleLimit, setChipVisibleLimit] = useState(pageSize)
  const [prevQuery, setPrevQuery] = useState(query)
  const [prevOpen, setPrevOpen] = useState(open)
  const [prevPageSize, setPrevPageSize] = useState(pageSize)
  const [prevValueLength, setPrevValueLength] = useState(value.length)
  const [activeIndex, setActiveIndex] = useState(0)

  if (prevQuery !== query || prevOpen !== open || prevPageSize !== pageSize) {
    setPrevQuery(query)
    setPrevOpen(open)
    setPrevPageSize(pageSize)
    setVisibleLimit(pageSize)
    if (prevPageSize !== pageSize) {
      setChipVisibleLimit(pageSize)
    }
  }

  if (prevValueLength !== value.length) {
    setPrevValueLength(value.length)
    setChipVisibleLimit(pageSize)
  }

  const anchorRef = useRef<HTMLDivElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const dropdownPos = useDropdownPosition(open, anchorRef, DROPDOWN_MAX_HEIGHT, minDropdownWidth)
  useClickOutside(open, [anchorRef, dropdownRef], () => setOpen(false))

  const listboxId = useId()

  const selectedSet = useMemo(() => new Set(value), [value])
  const lockedSet = useMemo(() => new Set(lockedValues), [lockedValues])

  const filtered = useMemo(
    () => filterPickerOptions(options, query, selectedSet),
    [options, query, selectedSet],
  )

  const { visible, remaining } = paginateItems(filtered, visibleLimit)
  const hasMore = remaining > 0
  const paginateChips = chipsPosition === 'below'
  const { visible: visibleChipValues, remaining: remainingChips } = paginateItems(
    value,
    paginateChips ? chipVisibleLimit : value.length,
  )
  const safeActiveIndex = visible.length === 0 ? 0 : Math.min(activeIndex, visible.length - 1)

  // Скроллим клавиатурно-активный опцион в зону видимости.
  useEffect(() => {
    if (!open || visible.length === 0) return
    const el = dropdownRef.current?.querySelector<HTMLElement>(
      `#${CSS.escape(`${listboxId}-opt-${safeActiveIndex}`)}`,
    )
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

  function openDropdown() {
    setOpen(true)
  }

  function applyPick(opt: SearchablePickerOption) {
    if (selectedSet.has(opt.value)) return
    onChange([...value, opt.value])
    setQuery('')
    setActiveIndex(0)
    openDropdown()
  }

  function focusInput() {
    inputRef.current?.focus({ preventScroll: true })
  }

  function pickOption(opt: SearchablePickerOption) {
    applyPick(opt)
    focusInput()
  }

  function removeValue(v: string) {
    if (lockedSet.has(v)) return
    onChange(value.filter((s) => s !== v))
  }

  function handleInputChange(e: ChangeEvent<HTMLInputElement>) {
    setQuery(e.target.value)
    setActiveIndex(0)
    openDropdown()
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

  function buildOptionA11y(opt: SearchablePickerOption, i: number): OptionA11yProps {
    const active = i === safeActiveIndex
    return {
      id: `${listboxId}-opt-${i}`,
      role: 'option',
      'aria-selected': selectedSet.has(opt.value),
      'data-active': active || undefined,
      onMouseEnter: () => setActiveIndex(i),
    }
  }

  function defaultRenderOption(
    opt: SearchablePickerOption,
    pick: () => void,
    a11y: OptionA11yProps,
  ) {
    return (
      <div
        key={opt.value}
        className={styles.option}
        {...a11y}
        onMouseDown={(e) => {
          e.preventDefault()
          pick()
        }}
      >
        <div className={styles.optionText}>
          <span className={styles.optionName}>{opt.label}</span>
          {opt.secondary && opt.secondary !== opt.label ? (
            <span className={styles.optionSecondary}>{opt.secondary}</span>
          ) : null}
        </div>
      </div>
    )
  }

  const dropdownPortal = open
    ? createPortal(
        <div
          ref={dropdownRef}
          id={listboxId}
          className={styles.dropdown}
          role="listbox"
          aria-label={chipsAriaLabel}
          data-portal-dropdown="searchable-picker"
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
              {visible.map((opt, i) =>
                renderOption
                  ? renderOption(opt, () => applyPick(opt), buildOptionA11y(opt, i))
                  : defaultRenderOption(opt, () => applyPick(opt), buildOptionA11y(opt, i)),
              )}
              {hasMore ? (
                <button
                  type="button"
                  className={styles.loadMore}
                  onMouseDown={(e) => {
                    e.preventDefault()
                    setVisibleLimit((n) => n + pageSize)
                  }}
                >
                  Ещё ({remaining})
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

  if (readOnly) {
    return (
      <div className={styles.wrapper}>
        {value.length === 0 ? (
          <div className={`form-input ${styles.readOnlyEmpty}`}>{placeholder}</div>
        ) : (
          <div className={styles.chipsWrap} data-open="true">
            <div className={styles.chipsInner}>
              <div className={styles.chips} aria-label={chipsAriaLabel}>
                {value.map((v) => (
                  <span key={v} className={styles.chip}>
                    <span className={styles.chipLabel}>{labelByValue(options, v)}</span>
                  </span>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    )
  }

  const chipsNode =
    !hideChips && value.length > 0 ? (
      <div
        className={
          chipsPosition === 'right' ? styles.chipsInlineRight : styles.chipsWrap
        }
        data-open={chipsPosition === 'below' ? 'true' : undefined}
      >
        <div className={chipsPosition === 'right' ? undefined : styles.chipsInner}>
          <div className={styles.chips} aria-label={chipsAriaLabel}>
            {visibleChipValues.map((v) => (
              <span key={v} className={styles.chip}>
                <span className={styles.chipLabel}>{labelByValue(options, v)}</span>
                {lockedSet.has(v) ? null : (
                  <button
                    type="button"
                    className={styles.chipRemove}
                    title="Убрать"
                    aria-label={`Убрать ${labelByValue(options, v)}`}
                    onMouseDown={(e) => {
                      e.preventDefault()
                      e.stopPropagation()
                      removeValue(v)
                    }}
                  >
                    ×
                  </button>
                )}
              </span>
            ))}
          </div>
          {paginateChips && remainingChips > 0 ? (
            <button
              type="button"
              className={styles.loadMore}
              onMouseDown={(e) => {
                e.preventDefault()
                e.stopPropagation()
                setChipVisibleLimit((n) => n + pageSize)
              }}
            >
              Ещё ({remainingChips})
            </button>
          ) : null}
        </div>
      </div>
    ) : null

  return (
    <div
      ref={anchorRef}
      className={chipsPosition === 'right' ? styles.wrapperRow : styles.wrapper}
    >
      <div className={styles.inputRow}>
        <input
          ref={inputRef}
          type="text"
          className={`form-input ${styles.input}`}
          role="combobox"
          aria-expanded={open}
          aria-controls={listboxId}
          aria-autocomplete="list"
          aria-activedescendant={open && visible[safeActiveIndex] ? `${listboxId}-opt-${safeActiveIndex}` : undefined}
          aria-label={placeholder}
          placeholder={placeholder}
          value={open ? query : ''}
          onChange={handleInputChange}
          onFocus={openDropdown}
          onKeyDown={handleInputKeyDown}
        />
      </div>
      {chipsNode}
      {dropdownPortal}
    </div>
  )
}
