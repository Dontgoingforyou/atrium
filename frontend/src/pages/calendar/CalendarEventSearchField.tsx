import { useEffect, useId, useMemo, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'

import { searchEvents } from '../../api/calendar/calendarApi'
import { useClickOutside } from '../../hooks/useClickOutside'
import { PORTAL_SEARCH_MIN_QUERY_LEN } from '../../constants/search'
import type { CalendarEventSearchHit } from '../../types/calendar'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { calendarQueryKeys } from './calendarQueryKeys'
import styles from '@/styles/modules/calendar/CalendarPage.module.css'
import narrow from '@/styles/modules/calendar/CalendarPageNarrow.module.css'

function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const t = window.setTimeout(() => setDebounced(value), delayMs)
    return () => window.clearTimeout(t)
  }, [value, delayMs])
  return debounced
}

type Props = {
  onSelect: (hit: CalendarEventSearchHit) => void
}

export function CalendarEventSearchField({ onSelect }: Props) {
  const [input, setInput] = useState('')
  const [open, setOpen] = useState(false)
  const [activeIndex, setActiveIndex] = useState(0)
  const wrapRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLUListElement>(null)
  const listboxId = useId()
  const debounced = useDebouncedValue(input.trim(), 320)

  const query = useQuery({
    queryKey: calendarQueryKeys.search(debounced),
    queryFn: () => searchEvents({ q: debounced, limit: 8 }),
    enabled: debounced.length >= PORTAL_SEARCH_MIN_QUERY_LEN,
    staleTime: 20_000,
  })

  const items = useMemo(() => query.data?.items ?? [], [query.data])
  const showPanel = open && debounced.length >= PORTAL_SEARCH_MIN_QUERY_LEN

  useClickOutside(open, [wrapRef], () => setOpen(false), 'mousedown')

  useEffect(() => {
    if (!open) return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        setOpen(false)
        inputRef.current?.focus()
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open])

  // Сброс активной опции при смене результатов (охраняемый setState в рендере — без effect).
  const [prevItems, setPrevItems] = useState(items)
  if (prevItems !== items) {
    setPrevItems(items)
    setActiveIndex(0)
  }

  // Скролл клавиатурно-активной опции в зону видимости
  useEffect(() => {
    if (!showPanel) return
    const el = listRef.current?.querySelector<HTMLElement>('[data-active]')
    el?.scrollIntoView({ block: 'nearest' })
  }, [showPanel, activeIndex, items])

  function selectHit(hit: CalendarEventSearchHit) {
    onSelect(hit)
    setInput('')
    setOpen(false)
    inputRef.current?.focus()
  }

  function onInputKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!showPanel || items.length === 0) {
      if (e.key === 'ArrowDown' && items.length > 0) setOpen(true)
      return
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActiveIndex((i) => (i + 1) % items.length)
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActiveIndex((i) => (i - 1 + items.length) % items.length)
    } else if (e.key === 'Enter') {
      e.preventDefault()
      const hit = items[activeIndex]
      if (hit) selectHit(hit)
    } else if (e.key === 'Escape') {
      setOpen(false)
    }
  }

  const activeOptionId = showPanel && items[activeIndex]
    ? `${listboxId}-opt-${activeIndex}`
    : undefined

  return (
    <div className={`${styles.searchWrap} ${narrow.searchWrap}`} ref={wrapRef}>
      <input
        ref={inputRef}
        type="search"
        className={`form-input ${styles.searchInput}`}
        placeholder="Поиск событий…"
        value={input}
        role="combobox"
        aria-label="Поиск событий календаря"
        aria-expanded={showPanel}
        aria-controls={listboxId}
        aria-autocomplete="list"
        aria-activedescendant={activeOptionId}
        onChange={(e) => {
          setInput(e.target.value)
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={onInputKeyDown}
      />
      {showPanel ? (
        <div
          id={listboxId}
          className={styles.searchDropdown}
          role="listbox"
          aria-label="Результаты поиска событий"
        >
          {query.isPending ? (
            <p className={styles.searchHint}>Ищем…</p>
          ) : query.isError ? (
            <p className={styles.searchError} role="alert">
              {userFacingMessageFromUnknown(query.error)}
            </p>
          ) : items.length === 0 ? (
            <p className={styles.searchHint}>Ничего не найдено</p>
          ) : (
            <ul className={styles.searchList} role="presentation" ref={listRef}>
              {items.map((hit, index) => {
                const id = `${listboxId}-opt-${index}`
                const active = index === activeIndex
                return (
                  <li key={hit.id} role="presentation">
                    <button
                      type="button"
                      id={id}
                      role="option"
                      aria-selected={active}
                      data-active={active || undefined}
                      className={styles.searchItem}
                      onMouseEnter={() => setActiveIndex(index)}
                      onMouseDown={(e) => {
                        e.preventDefault()
                        selectHit(hit)
                      }}
                    >
                      <span className={styles.searchItemTitle}>{hit.title}</span>
                      <span className={styles.searchItemMeta}>
                        {hit.calendar_title}
                        {hit.location ? ` · ${hit.location}` : ''}
                      </span>
                    </button>
                  </li>
                )
              })}
            </ul>
          )}
        </div>
      ) : null}
    </div>
  )
}
