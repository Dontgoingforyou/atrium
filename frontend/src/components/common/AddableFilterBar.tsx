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
  ADDABLE_FILTER_ADD_LABEL,
  ADDABLE_FILTER_MENU_SEARCH_PLACEHOLDER,
  ADDABLE_FILTER_MENU_SECTION,
  ADDABLE_FILTER_RESET_LABEL,
} from './addableFilterBarConstants'
import {
  addActiveFieldId,
  formatFilterChipSummary,
  initActiveFieldIds,
  removeActiveFieldId,
  shouldOpenPickerOnAdd,
  shouldShowAddFilterMenu,
  syncActiveFieldIds,
} from './addableFilterBarUtils'
import styles from '@/styles/modules/ui/AddableFilterBar.module.css'

const PICKER_PORTAL_IGNORE = '[data-portal-dropdown]'

export type AddableFilterPickerApi = {
  close: () => void
}

export type AddableFilterField = {
  id: string
  label: string
  hasValues: boolean
  selectedLabels: string[]
  /** false — скрыть из меню и убрать активный чип (например исполнители вне team). */
  isAvailable?: boolean
  /** Показать чип даже без выбранных значений. */
  defaultActive?: boolean
  /** Вызвать при добавлении поля из меню «+ Добавить фильтр». */
  onActivate?: () => void
  onClear: () => void
  /** false — не открывать пикер при добавлении поля из меню. */
  openOnAdd?: boolean
  renderPicker?: (api: AddableFilterPickerApi) => ReactNode
}

type Props = {
  fields: AddableFilterField[]
  hasActiveFilters: boolean
  resetFilters: () => void
}

function toFieldSeed(f: AddableFilterField) {
  return { id: f.id, hasValues: f.hasValues, defaultActive: f.defaultActive }
}

function FilterChip({
  field,
  open,
  onToggle,
  onRemove,
}: {
  field: AddableFilterField
  open: boolean
  onToggle: () => void
  onRemove: () => void
}) {
  const anchorRef = useRef<HTMLDivElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const pos = useDropdownPosition(open, anchorRef, 380)

  useClickOutside(open, [anchorRef, dropdownRef], () => onToggle(), 'click', PICKER_PORTAL_IGNORE)

  const hasPicker = typeof field.renderPicker === 'function'

  return (
    <div ref={anchorRef} className={styles.chipWrap}>
      <div className={`${styles.chip} ${open ? styles.chipOpen : ''}`}>
        {hasPicker ? (
        <button
          type="button"
          className={styles.chipMain}
          aria-expanded={open}
          onClick={onToggle}
        >
          <span className={styles.chipSummary}>
            {formatFilterChipSummary(field.label, field.selectedLabels)}
          </span>
        </button>
        ) : (
        <span className={styles.chipMain}>
          <span className={styles.chipSummary}>
            {formatFilterChipSummary(field.label, field.selectedLabels)}
          </span>
        </span>
        )}
        <button
          type="button"
          className={styles.chipRemove}
          title="Убрать фильтр"
          aria-label={`Убрать фильтр «${field.label}»`}
          onClick={onRemove}
        >
          ×
        </button>
      </div>
      {open && hasPicker && field.renderPicker
        ? createPortal(
            <div
              ref={dropdownRef}
              className={styles.pickerPanel}
              style={{ top: pos.top, left: pos.left, width: pos.width, maxHeight: pos.maxHeight }}
            >
              {field.renderPicker({ close: onToggle })}
            </div>,
            document.body,
          )
        : null}
    </div>
  )
}

function fieldAvailabilityKey(fields: readonly AddableFilterField[]): string {
  return fields
    .map(
      (f) =>
        `${f.id}:${f.isAvailable === false ? 0 : 1}:${f.hasValues ? 1 : 0}:${f.defaultActive ? 1 : 0}`,
    )
    .join('|')
}

export function AddableFilterBar({ fields, hasActiveFilters, resetFilters }: Props) {
  const availableFields = useMemo(
    () => fields.filter((f) => f.isAvailable !== false),
    [fields],
  )
  const availabilityKey = fieldAvailabilityKey(fields)

  const [activeFieldIds, setActiveFieldIds] = useState(() =>
    initActiveFieldIds(availableFields.map(toFieldSeed)),
  )
  const [prevAvailabilityKey, setPrevAvailabilityKey] = useState(availabilityKey)
  const [menuOpen, setMenuOpen] = useState(false)
  const [menuQuery, setMenuQuery] = useState('')
  const [menuActiveIndex, setMenuActiveIndex] = useState(-1)
  const [openFieldId, setOpenFieldId] = useState<string | null>(null)

  const listboxId = useId()
  const menuOptionRefs = useRef<Array<HTMLButtonElement | null>>([])
  const addMenuRef = useRef<HTMLDivElement>(null)
  const menuSearchRef = useRef<HTMLInputElement>(null)
  const menuAnchorRef = useRef<HTMLButtonElement>(null)
  const menuDropdownRef = useRef<HTMLDivElement>(null)
  const menuPos = useDropdownPosition(menuOpen, menuAnchorRef, 380)

  if (prevAvailabilityKey !== availabilityKey) {
    setPrevAvailabilityKey(availabilityKey)
    setActiveFieldIds((prev) => syncActiveFieldIds(prev, availableFields.map(toFieldSeed)))
    if (openFieldId && !availableFields.some((f) => f.id === openFieldId)) {
      setOpenFieldId(null)
    }
  }

  useClickOutside(
    menuOpen,
    [addMenuRef, menuDropdownRef],
    () => {
      setMenuOpen(false)
      setMenuQuery('')
    },
  )

  const activeFields = availableFields.filter((f) => activeFieldIds.includes(f.id))
  const inactiveFields = availableFields.filter((f) => !activeFieldIds.includes(f.id))
  const menuFiltered = inactiveFields.filter((f) => {
    const q = menuQuery.trim().toLowerCase()
    if (!q) return true
    return f.label.toLowerCase().includes(q)
  })

  function handleAddField(fieldId: string) {
    const field = availableFields.find((f) => f.id === fieldId)
    field?.onActivate?.()
    setActiveFieldIds((prev) => addActiveFieldId(prev, fieldId))
    setMenuOpen(false)
    setMenuQuery('')
    setMenuActiveIndex(-1)
    if (
      field &&
      shouldOpenPickerOnAdd({
        hasPicker: typeof field.renderPicker === 'function',
        openOnAdd: field.openOnAdd,
      })
    ) {
      setOpenFieldId(fieldId)
    }
  }

  function handleRemoveField(field: AddableFilterField) {
    field.onClear()
    setActiveFieldIds((prev) => removeActiveFieldId(prev, field.id))
    if (openFieldId === field.id) setOpenFieldId(null)
  }

  function handleResetAll() {
    resetFilters()
    setActiveFieldIds(
      initActiveFieldIds(
        availableFields.map((f) => ({ id: f.id, hasValues: false, defaultActive: f.defaultActive })),
      ),
    )
    setOpenFieldId(null)
    setMenuOpen(false)
    setMenuActiveIndex(-1)
  }

  function handleMenuQueryChange(e: ChangeEvent<HTMLInputElement>) {
    setMenuQuery(e.target.value)
    setMenuActiveIndex(-1)
  }

  // При открытии меню — фокус в поле поиска. Сброс подсветки — в handleMenuQueryChange.
  useEffect(() => {
    if (!menuOpen) return
    menuSearchRef.current?.focus()
  }, [menuOpen])

  useEffect(() => {
    if (menuActiveIndex < 0) return
    menuOptionRefs.current[menuActiveIndex]?.scrollIntoView({ block: 'nearest' })
  }, [menuActiveIndex])

  function onMenuSearchKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Escape') {
      e.preventDefault()
      setMenuOpen(false)
      setMenuQuery('')
      setMenuActiveIndex(-1)
      return
    }
    if (menuFiltered.length === 0) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setMenuActiveIndex((i) => (i < 0 ? 0 : Math.min(menuFiltered.length - 1, i + 1)))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setMenuActiveIndex((i) => (i <= 0 ? menuFiltered.length - 1 : i - 1))
    } else if (e.key === 'Enter') {
      const picked = menuActiveIndex >= 0 ? menuFiltered[menuActiveIndex] : null
      if (picked) {
        e.preventDefault()
        handleAddField(picked.id)
      }
    }
  }

  return (
    <div className={styles.bar}>
      <div className={styles.chipsRow}>
        {activeFields.map((field) => (
          <FilterChip
            key={field.id}
            field={field}
            open={openFieldId === field.id}
            onToggle={() =>
              setOpenFieldId(openFieldId === field.id ? null : field.id)
            }
            onRemove={() => handleRemoveField(field)}
          />
        ))}
      </div>

      {shouldShowAddFilterMenu(inactiveFields.length) ? (
      <div className={styles.addWrap} ref={addMenuRef}>
        <button
          type="button"
          ref={menuAnchorRef}
          className={`${styles.addBtn} ${menuOpen ? styles.addBtnOpen : ''}`}
          aria-haspopup="listbox"
          aria-expanded={menuOpen}
          aria-controls={listboxId}
          onClick={() => setMenuOpen((v) => !v)}
        >
          {ADDABLE_FILTER_ADD_LABEL}
        </button>
        {menuOpen
          ? createPortal(
              <div
                ref={menuDropdownRef}
                className={styles.menu}
                id={listboxId}
                role="listbox"
                aria-label={ADDABLE_FILTER_ADD_LABEL}
                style={{ top: menuPos.top, left: menuPos.left, width: menuPos.width }}
              >
            <input
              ref={menuSearchRef}
              type="text"
              className={`form-input ${styles.menuSearch}`}
              placeholder={ADDABLE_FILTER_MENU_SEARCH_PLACEHOLDER}
              value={menuQuery}
              onChange={handleMenuQueryChange}
              onKeyDown={onMenuSearchKeyDown}
              role="combobox"
              aria-expanded={menuOpen}
              aria-haspopup="listbox"
              aria-autocomplete="list"
              aria-controls={listboxId}
              aria-activedescendant={
                menuActiveIndex >= 0 ? `${listboxId}-opt-${menuActiveIndex}` : undefined
              }
            />
            <p className={styles.menuSection}>{ADDABLE_FILTER_MENU_SECTION}</p>
            <div className={styles.menuList}>
              {menuFiltered.length === 0 ? (
                <p className={styles.menuEmpty}>Нет доступных полей</p>
              ) : (
                menuFiltered.map((field, index) => (
                  <button
                    key={field.id}
                    ref={(el) => { menuOptionRefs.current[index] = el }}
                    id={`${listboxId}-opt-${index}`}
                    type="button"
                    className={styles.menuItem}
                    role="option"
                    aria-selected={menuActiveIndex === index}
                    onMouseEnter={() => setMenuActiveIndex(index)}
                    onClick={() => handleAddField(field.id)}
                  >
                    {field.label}
                  </button>
                ))
              )}
            </div>
              </div>,
              document.body,
            )
          : null}
      </div>
      ) : null}

      {hasActiveFilters ? (
        <button type="button" className={styles.resetBtn} onClick={handleResetAll}>
          {ADDABLE_FILTER_RESET_LABEL}
        </button>
      ) : null}
    </div>
  )
}
