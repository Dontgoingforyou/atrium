import { useEffect, useId, useMemo, useRef, useState } from 'react'

import type { SpecialistColumn } from '../../types/specialist'
import {
  buildSpecialistColumnSelectOptions,
  specialistColumnsAsTaskColumns,
} from '../../domain/specialists/specialistBoardPref'
import { getTaskColumnColor, getTaskColumnTitle } from '../../domain/tasks/taskColumns'
import { useClickOutside } from '../../hooks/useClickOutside'
import taskRowStyles from '@/styles/modules/tasks/TasksPageTaskRow.module.css'

interface Props {
  columns: SpecialistColumn[]
  currentColumnKey: string
  disabled?: boolean
  onChange: (columnKey: string) => void
}

export function SpecialistKanbanColumnSelect({
  columns,
  currentColumnKey,
  disabled = false,
  onChange,
}: Props) {
  const taskColumns = useMemo(() => specialistColumnsAsTaskColumns(columns), [columns])
  const columnOptions = useMemo(
    () => buildSpecialistColumnSelectOptions(columns, currentColumnKey),
    [columns, currentColumnKey],
  )
  const columnColor = getTaskColumnColor(currentColumnKey, taskColumns)
  const columnLabel = getTaskColumnTitle(currentColumnKey, taskColumns)

  const [columnMenuOpen, setColumnMenuOpen] = useState(false)
  const [columnActiveIndex, setColumnActiveIndex] = useState(-1)
  const columnMenuWrapRef = useRef<HTMLSpanElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const columnMenuId = useId()
  const optionId = (idx: number) => `${columnMenuId}-opt-${idx}`

  function closeColumnMenu() {
    setColumnMenuOpen(false)
    setColumnActiveIndex(-1)
    triggerRef.current?.focus()
  }

  function openColumnMenu() {
    setColumnMenuOpen(true)
    setColumnActiveIndex(columnOptions.length > 0 ? 0 : -1)
  }

  useClickOutside(columnMenuOpen, [columnMenuWrapRef], closeColumnMenu)

  useEffect(() => {
    if (columnActiveIndex < 0) return
    const el = document.getElementById(`${columnMenuId}-opt-${columnActiveIndex}`)
    el?.scrollIntoView({ block: 'nearest' })
  }, [columnActiveIndex, columnMenuId])

  function selectColumn(value: string) {
    closeColumnMenu()
    if (value !== currentColumnKey) onChange(value)
  }

  function onColumnTriggerKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault()
      if (!columnMenuOpen) {
        openColumnMenu()
        return
      }
      const dir = e.key === 'ArrowDown' ? 1 : -1
      setColumnActiveIndex((i) => {
        const n = columnOptions.length
        if (n === 0) return i
        return (i + dir + n) % n
      })
    } else if (e.key === 'Enter' && columnMenuOpen && columnActiveIndex >= 0) {
      e.preventDefault()
      selectColumn(columnOptions[columnActiveIndex].value)
    } else if (e.key === 'Escape') {
      e.preventDefault()
      closeColumnMenu()
    }
  }

  return (
    <span className={taskRowStyles.statusSelectWrap} ref={columnMenuWrapRef}>
      <button
        ref={triggerRef}
        type="button"
        role="combobox"
        disabled={disabled}
        onPointerDown={(e) => e.stopPropagation()}
        onClick={(e) => {
          e.stopPropagation()
          if (columnMenuOpen) closeColumnMenu()
          else openColumnMenu()
        }}
        onKeyDown={onColumnTriggerKeyDown}
        className={taskRowStyles.statusSelect}
        style={{
          border: `1px solid ${columnColor}`,
          color: columnColor,
        }}
        aria-haspopup="listbox"
        aria-expanded={columnMenuOpen}
        aria-controls={columnMenuId}
        aria-autocomplete="list"
        aria-activedescendant={
          columnMenuOpen && columnActiveIndex >= 0 ? optionId(columnActiveIndex) : undefined
        }
        aria-label="Колонка воронки"
      >
        {columnLabel}
        <span className={taskRowStyles.statusSelectArrow} aria-hidden>
          ⇕
        </span>
      </button>
      {columnMenuOpen ? (
        <div
          className={taskRowStyles.statusMenu}
          role="listbox"
          id={columnMenuId}
          aria-label="Колонка воронки"
          onPointerDown={(e) => e.stopPropagation()}
        >
          {columnOptions.map((opt, idx) => (
            <button
              key={opt.value}
              id={optionId(idx)}
              type="button"
              role="option"
              aria-selected={opt.value === currentColumnKey}
              className={taskRowStyles.statusMenuItem}
              style={{ color: opt.color }}
              data-active={idx === columnActiveIndex ? 'true' : undefined}
              onMouseEnter={() => setColumnActiveIndex(idx)}
              onClick={(e) => {
                e.stopPropagation()
                selectColumn(opt.value)
              }}
            >
              {opt.label}
            </button>
          ))}
        </div>
      ) : null}
    </span>
  )
}
