import { type ChangeEvent, useEffect, useId, useMemo, useRef, useState } from 'react'
import type { MouseEvent } from 'react'
import { createPortal } from 'react-dom'
import type { PortalUserShort } from '../../api/usersApi'
import { usePortalUserDirectory } from '../../hooks/usePortalUserDirectory'
import { useClickOutside } from '../../hooks/useClickOutside'
import { useDropdownPosition } from '../../hooks/useDropdownPosition'
import { UserAvatar } from '../ui/UserAvatar'
import { getUserDisplayLabel } from '../../utils/userLabel'
import styles from '@/styles/modules/ui/UserPicker.module.css'

interface UserPickerProps {
  value: string
  onChange: (sub: string, displayName: string) => void
  placeholder?: string
  limit?: number
  readOnly?: boolean
  invalid?: boolean
}

const DROPDOWN_MAX_HEIGHT = 240
const DROPDOWN_MIN_WIDTH = 420

export function UserPicker({
  value,
  onChange,
  placeholder = 'Начните вводить имя…',
  limit = 500,
  readOnly = false,
  invalid = false,
}: UserPickerProps) {
  const [query, setQuery] = useState('')
  const [displayValue, setDisplayValue] = useState('')
  /** После × не показывать stale label, пока родитель не сбросил value */
  const [suppressLabel, setSuppressLabel] = useState(false)
  const [valueSnapshot, setValueSnapshot] = useState(value)
  const [open, setOpen] = useState(false)
  const [activeIndex, setActiveIndex] = useState(0)

  const anchorRef = useRef<HTMLDivElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const dropdownPos = useDropdownPosition(open, anchorRef, DROPDOWN_MAX_HEIGHT, DROPDOWN_MIN_WIDTH)
  useClickOutside(open, [anchorRef, dropdownRef], () => setOpen(false), 'mousedown')

  const listboxId = useId()

  const { users: allUsers, isError } = usePortalUserDirectory({ limit })

  // Синхронизация с value без useEffect (избегаем set-state-in-effect)
  if (value !== valueSnapshot) {
    setValueSnapshot(value)
    setSuppressLabel(false)
    if (!value) {
      setDisplayValue('')
      setQuery('')
    }
  }

  const filtered = useMemo(() => {
    if (!query.trim()) return allUsers.slice(0, 10)
    const q = query.toLowerCase()
    return allUsers
      .filter(
        (u) =>
          u.display_name?.toLowerCase().includes(q) ||
          u.email?.toLowerCase().includes(q) ||
          u.username?.toLowerCase().includes(q) ||
          u.sub.toLowerCase().includes(q),
      )
      .slice(0, 10)
  }, [allUsers, query])

  const safeActiveIndex = filtered.length === 0 ? 0 : Math.min(activeIndex, filtered.length - 1)

  // Скроллим клавиатурно-активный опцион в зону видимости.
  useEffect(() => {
    if (!open || filtered.length === 0) return
    const el = dropdownRef.current?.querySelector<HTMLElement>(
      `#${CSS.escape(`${listboxId}-opt-${safeActiveIndex}`)}`,
    )
    el?.scrollIntoView({ block: 'nearest' })
  }, [open, safeActiveIndex, listboxId, filtered.length])

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

  const resolvedLabel = (() => {
    if (suppressLabel) return ''
    if (displayValue) return displayValue
    if (value && allUsers.length > 0) {
      const found = allUsers.find((u) => u.sub === value)
      if (found) return getUserDisplayLabel(found)
      return value
    }
    return ''
  })()

  function handleSelect(u: PortalUserShort) {
    const label = getUserDisplayLabel(u)
    setSuppressLabel(false)
    setDisplayValue(label)
    setQuery(label)
    setOpen(false)
    onChange(u.sub, label)
    inputRef.current?.blur()
  }

  function handleInputChange(e: ChangeEvent<HTMLInputElement>) {
    setSuppressLabel(false)
    setQuery(e.target.value)
    setDisplayValue('')
    setOpen(true)
    setActiveIndex(0)
    if (!e.target.value.trim()) {
      setSuppressLabel(true)
      onChange('', '')
    }
  }

  function handleInputKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!open) return
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setActiveIndex(filtered.length === 0 ? 0 : Math.min(safeActiveIndex + 1, filtered.length - 1))
        break
      case 'ArrowUp':
        e.preventDefault()
        setActiveIndex(Math.max(safeActiveIndex - 1, 0))
        break
      case 'Enter':
        if (filtered[safeActiveIndex]) {
          e.preventDefault()
          handleSelect(filtered[safeActiveIndex])
        }
        break
      case 'Escape':
        e.preventDefault()
        setOpen(false)
        break
    }
  }

  function handleClear(e: MouseEvent<HTMLButtonElement>) {
    e.preventDefault()
    e.stopPropagation()
    setSuppressLabel(true)
    setQuery('')
    setDisplayValue('')
    setOpen(false)
    onChange('', '')
  }

  if (readOnly) {
    return (
      <div className={styles.wrapper}>
        <div className={`form-input ${styles.readOnlyValue}`}>
          {resolvedLabel || placeholder}
        </div>
      </div>
    )
  }

  const dropdownPortal =
    open && filtered.length > 0
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
            {filtered.map((u, i) => {
              const active = i === safeActiveIndex
              return (
                <div
                  key={u.sub}
                  id={`${listboxId}-opt-${i}`}
                  className={styles.option}
                  role="option"
                  aria-selected={u.sub === value}
                  data-active={active || undefined}
                  onMouseDown={(e) => {
                    e.preventDefault()
                    handleSelect(u)
                  }}
                  onMouseEnter={() => setActiveIndex(i)}
                >
                  <UserAvatar size="sm" label={getUserDisplayLabel(u)} imageUrl={u.avatar_url} />
                  <div className={styles.optionText}>
                    <span className={styles.optionName}>{getUserDisplayLabel(u)}</span>
                    {u.email && u.email !== getUserDisplayLabel(u) && (
                      <span className={styles.optionEmail}>{u.email}</span>
                    )}
                  </div>
                </div>
              )
            })}
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
          className={['form-input', invalid ? 'form-input-invalid' : ''].filter(Boolean).join(' ')}
          role="combobox"
          aria-expanded={open}
          aria-controls={listboxId}
          aria-autocomplete="list"
          aria-activedescendant={open && filtered[safeActiveIndex] ? `${listboxId}-opt-${safeActiveIndex}` : undefined}
          aria-label={placeholder}
          placeholder={placeholder}
          value={open ? query : resolvedLabel || query}
          aria-invalid={invalid || undefined}
          onChange={handleInputChange}
          onKeyDown={handleInputKeyDown}
          onFocus={() => {
            setQuery(resolvedLabel || '')
            setOpen(true)
          }}
        />
        {value || query ? (
          <button
            type="button"
            className={styles.clearBtn}
            onMouseDown={(e) => {
              e.preventDefault()
              handleClear(e)
            }}
            title="Очистить"
            aria-label="Очистить"
          >
            ×
          </button>
        ) : null}
      </div>
      {isError && open ? (
        <p className={styles.errorHint} role="alert">
          Ошибка загрузки списка пользователей
        </p>
      ) : null}
      {dropdownPortal}
    </div>
  )
}
