import { useEffect, useId, useMemo, useRef, useState, type KeyboardEvent as ReactKeyboardEvent } from 'react'
import { useQuery } from '@tanstack/react-query'

import { listSharedCalendars } from '../../api/calendar/calendarApi'
import {
  departmentGroupKey,
  departmentLabel,
  departmentsMatchingQuery,
  groupCalendarsByDepartment,
  type DepartmentCalendarGroup,
} from '../../domain/calendar/sharedDepartments'
import { calendarQueryKeys } from './calendarQueryKeys'
import { useClickOutside } from '../../hooks/useClickOutside'
import { useAuthStore } from '../../store/authStore'
import type { SharedDepartmentCalendar } from '../../types/calendar'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import styles from '@/styles/modules/calendar/CalendarPage.module.css'

const CLEAR_PERSON_LABEL = 'Сбросить выбор человека'

type Props = {
  onPickPerson: (ownerSub: string) => void
  onDepartmentChange: () => void
  onClearPerson: () => void
}

function personCaption(title: string, ownerLabel: string | null): string {
  const name = ownerLabel?.trim() || 'Владелец'
  if (!title || title === name) return name
  return `${name} · ${title}`
}

export function CalendarAdminTools({ onPickPerson, onDepartmentChange, onClearPerson }: Props) {
  const isAdmin = useAuthStore((s) => s.user?.is_portal_admin ?? false)
  const gid = useAuthStore((s) => s.user?.gid_number ?? null)
  const ownKey = gid?.trim() ?? ''
  const [query, setQuery] = useState(() => departmentLabel(gid))
  const [selectedKey, setSelectedKey] = useState<string | null>(ownKey)

  const sharedQuery = useQuery({
    queryKey: calendarQueryKeys.shared,
    queryFn: listSharedCalendars,
    enabled: isAdmin,
  })
  const groups = useMemo(
    () => groupCalendarsByDepartment(sharedQuery.data ?? []),
    [sharedQuery.data],
  )
  const selected = groups.find((group) => departmentGroupKey(group) === selectedKey) ?? null

  if (!isAdmin) return null

  return (
    <>
      <DepartmentField
        groups={groups}
        pending={sharedQuery.isPending}
        errorText={sharedQuery.isError ? userFacingMessageFromUnknown(sharedQuery.error) : null}
        query={query}
        selected={selected}
        onQueryChange={setQuery}
        onClear={() => setSelectedKey(null)}
        onPick={(group) => {
          setSelectedKey(departmentGroupKey(group))
          setQuery(group.label)
          onDepartmentChange()
        }}
      />
      <PeopleField
        people={selected?.calendars ?? []}
        pending={sharedQuery.isPending}
        onPick={onPickPerson}
        onClearPerson={onClearPerson}
      />
    </>
  )
}

function DepartmentField({
  groups,
  pending,
  errorText,
  query,
  selected,
  onQueryChange,
  onClear,
  onPick,
}: {
  groups: DepartmentCalendarGroup[]
  pending: boolean
  errorText: string | null
  query: string
  selected: DepartmentCalendarGroup | null
  onQueryChange: (value: string) => void
  onClear: () => void
  onPick: (group: DepartmentCalendarGroup) => void
}) {
  const [open, setOpen] = useState(false)
  const [searching, setSearching] = useState(false)
  const [activeIndex, setActiveIndex] = useState(0)
  const anchorRef = useRef<HTMLDivElement>(null)
  const listRef = useRef<HTMLUListElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const listboxId = useId()
  const filtered = useMemo(
    () => departmentsMatchingQuery(groups, searching ? query : '').filter((group) => group.label),
    [groups, query, searching],
  )
  const safeIndex = filtered.length === 0 ? 0 : Math.min(activeIndex, filtered.length - 1)
  const activeOptionId = filtered.length > 0 ? `${listboxId}-opt-${safeIndex}` : undefined

  useClickOutside(open, [anchorRef], () => setOpen(false), 'mousedown')

  useEffect(() => {
    if (!open) return
    listRef.current?.querySelector<HTMLElement>(`[data-active='true']`)?.scrollIntoView({ block: 'nearest' })
  }, [open, safeIndex])

  useEffect(() => {
    if (!open) return
    function onKey(event: globalThis.KeyboardEvent) {
      if (event.key !== 'Escape') return
      event.preventDefault()
      setOpen(false)
      inputRef.current?.focus()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open])

  function onInputKeyDown(event: ReactKeyboardEvent<HTMLInputElement>) {
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setOpen(true)
      setActiveIndex((index) => Math.min(index + (open ? 1 : 0), Math.max(filtered.length - 1, 0)))
      return
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault()
      setOpen(true)
      setActiveIndex((index) => Math.max(index - 1, 0))
      return
    }
    if (event.key === 'Enter' && open && filtered[safeIndex]) {
      event.preventDefault()
      setSearching(false)
      onPick(filtered[safeIndex])
      setOpen(false)
      return
    }
    if (event.key === 'Escape') {
      event.preventDefault()
      setOpen(false)
    }
  }

  return (
    <div className={styles.departmentSearch} ref={anchorRef}>
      <input
        ref={inputRef}
        className={`form-input ${styles.searchInput}`}
        role="combobox"
        aria-expanded={open}
        aria-controls={listboxId}
        aria-autocomplete="list"
        aria-activedescendant={open ? activeOptionId : undefined}
        aria-label="Поиск по отделам"
        placeholder="Отдел…"
        value={query}
        onChange={(event) => {
          const next = event.target.value
          onQueryChange(next)
          setSearching(true)
          setOpen(true)
          setActiveIndex(0)
          if (selected && next.trim().toLowerCase() !== selected.label.toLowerCase()) {
            onClear()
          }
        }}
        onFocus={() => {
          setSearching(false)
          setOpen(true)
        }}
        onKeyDown={onInputKeyDown}
      />
      {errorText ? (
        <p className="text-danger" role="alert">
          {errorText}
        </p>
      ) : null}
      {open ? (
        <ul ref={listRef} id={listboxId} className={styles.searchDropdown} role="listbox" aria-label="Отделы">
          {filtered.length === 0 ? (
            <li className={styles.searchHint}>
              {pending ? 'Загрузка…' : groups.length === 0 ? 'Нет календарей, открытых другим отделам' : 'Нет такого отдела'}
            </li>
          ) : (
            filtered.map((group, index) => (
              <li key={departmentGroupKey(group) || 'none'}>
                <button
                  type="button"
                  id={`${listboxId}-opt-${index}`}
                  role="option"
                  aria-selected={index === safeIndex}
                  data-active={index === safeIndex ? 'true' : undefined}
                  className={styles.searchItem}
                  onMouseEnter={() => setActiveIndex(index)}
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => {
                    setSearching(false)
                    onPick(group)
                    setOpen(false)
                  }}
                >
                  {group.label}
                </button>
              </li>
            ))
          )}
        </ul>
      ) : null}
    </div>
  )
}

function PeopleField({
  people,
  pending,
  onPick,
  onClearPerson,
}: {
  people: SharedDepartmentCalendar[]
  pending: boolean
  onPick: (ownerSub: string) => void
  onClearPerson: () => void
}) {
  const [open, setOpen] = useState(false)
  const [activeIndex, setActiveIndex] = useState(0)
  const [picked, setPicked] = useState('')
  const peopleKey = people.map((calendar) => calendar.id).join('\n')
  const [seenPeopleKey, setSeenPeopleKey] = useState(peopleKey)
  if (peopleKey !== seenPeopleKey) {
    setSeenPeopleKey(peopleKey)
    setPicked('')
  }
  const anchorRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const listboxId = useId()
  const safeIndex = people.length === 0 ? 0 : Math.min(activeIndex, people.length - 1)

  useClickOutside(open, [anchorRef], () => setOpen(false), 'mousedown')

  function pick(calendar: SharedDepartmentCalendar) {
    setPicked(personCaption(calendar.title, calendar.owner_label))
    setOpen(false)
    onPick(calendar.owner_sub)
  }

  function clearPerson() {
    setPicked('')
    setOpen(false)
    onClearPerson()
  }

  function onInputKeyDown(event: ReactKeyboardEvent<HTMLInputElement>) {
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setOpen(true)
      setActiveIndex((index) => Math.min(index + (open ? 1 : 0), Math.max(people.length - 1, 0)))
      return
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault()
      setOpen(true)
      setActiveIndex((index) => Math.max(index - 1, 0))
      return
    }
    if (event.key === 'Enter' && open && people[safeIndex]) {
      event.preventDefault()
      pick(people[safeIndex])
      return
    }
    if (event.key === 'Escape') {
      event.preventDefault()
      setOpen(false)
    }
  }

  return (
    <div className={styles.departmentSearch} ref={anchorRef} data-tour="calendar-peer-picker">
      <input
        ref={inputRef}
        className={`form-input ${styles.searchInput}${picked ? ` ${styles.searchInputWithClear}` : ''}`}
        role="combobox"
        aria-expanded={open}
        aria-controls={listboxId}
        aria-label="Участник отдела"
        placeholder="Участник отдела…"
        value={picked}
        readOnly
        onFocus={() => setOpen(true)}
        onClick={() => setOpen(true)}
        onKeyDown={onInputKeyDown}
      />
      {picked ? (
        <button
          type="button"
          className={styles.clearPersonBtn}
          onMouseDown={(event) => event.preventDefault()}
          onClick={clearPerson}
          title={CLEAR_PERSON_LABEL}
          aria-label={CLEAR_PERSON_LABEL}
        >
          ×
        </button>
      ) : null}
      {open ? (
        <ul id={listboxId} className={`${styles.searchDropdown} ${styles.departmentPeople}`} role="listbox" aria-label="Участники отдела">
          {people.length === 0 ? (
            <li className={styles.searchHint}>
              {pending ? 'Загрузка…' : 'В этом отделе нет открытых календарей'}
            </li>
          ) : (
            people.map((calendar, index) => (
              <li key={calendar.id}>
                <button
                  type="button"
                  role="option"
                  aria-selected={index === safeIndex}
                  data-active={index === safeIndex ? 'true' : undefined}
                  className={styles.departmentPerson}
                  onMouseEnter={() => setActiveIndex(index)}
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => pick(calendar)}
                >
                  {personCaption(calendar.title, calendar.owner_label)}
                </button>
              </li>
            ))
          )}
        </ul>
      ) : null}
    </div>
  )
}
