import type { ManagerSpecialistEntry, SpecialistBoardPref, SpecialistColumn } from '../../types/specialist'
import type { PortalTaskColumn } from '../../types/task'
import {
  buildDisplayOrderWithOtherBucket,
  KANBAN_OTHER_BUCKET,
  mergeOrderedKeys,
} from '../kanban/kanbanDisplayCommon'
import { buildTaskStatusSelectOptions } from '../tasks/taskColumns'

export function specialistColumnsAsTaskColumns(columns: SpecialistColumn[]): PortalTaskColumn[] {
  return columns.map((c) => ({
    id: c.id,
    title: c.title,
    color: c.color,
    status_key: c.key,
    position: c.position,
    exclude_from_kpi: false,
  }))
}

export const SPECIALIST_MOVE_NOT_ON_MY_BOARD =
  'Нельзя перенести карточку: специалист не на вашей доске'

export function hiddenColumnKeysAfterSelect(hiddenKeys: string[], selectedColumnKey: string): string[] {
  return hiddenKeys.filter((key) => key !== selectedColumnKey)
}

export function findOwnBoardEntry(
  entries: ManagerSpecialistEntry[],
  specialistSub: string,
  currentUserSub: string,
): ManagerSpecialistEntry | undefined {
  return entries.find((e) => e.specialist_sub === specialistSub && e.manager_sub === currentUserSub)
}

export function buildSpecialistColumnSelectOptions(
  columns: SpecialistColumn[],
  currentColumnKey?: string,
) {
  return buildTaskStatusSelectOptions(specialistColumnsAsTaskColumns(columns), currentColumnKey)
}

/** Порядок колонок: сохранённый порядок + недостающие по position. */
export function mergeSpecialistColumnOrder(
  columns: SpecialistColumn[],
  pref: SpecialistBoardPref | null | undefined,
): string[] {
  const keys = columns.map((c) => c.key)
  const positionByKey = new Map(columns.map((c) => [c.key, c.position]))
  return mergeOrderedKeys(keys, pref?.column_order, positionByKey)
}

export function computeSpecialistKanbanDisplay(
  columnOrder: string[],
  entries: ManagerSpecialistEntry[],
  pref: SpecialistBoardPref | null | undefined,
  showAllHiddenColumns: boolean,
): {
  displayColumnKeys: string[]
  entriesForColumn: (colKey: string) => ManagerSpecialistEntry[]
} {
  const hidden = new Set(pref?.hidden_column_keys ?? [])
  const hiddenEntries = showAllHiddenColumns
    ? []
    : entries.filter((e) => hidden.has(e.column_key))

  const displayColumnKeys = buildDisplayOrderWithOtherBucket(
    columnOrder,
    hidden,
    showAllHiddenColumns,
    hiddenEntries.length > 0,
  )

  const entriesForColumn = (colKey: string): ManagerSpecialistEntry[] => {
    if (colKey === KANBAN_OTHER_BUCKET) {
      return [...hiddenEntries].sort((a, b) => a.position - b.position)
    }
    return entries
      .filter((e) => e.column_key === colKey)
      .sort((a, b) => a.position - b.position)
  }

  return { displayColumnKeys, entriesForColumn }
}

/** Одна карточка на специалиста в колонке (режим «Все специалисты»). */
export function groupKanbanEntriesBySpecialist(
  columnEntries: ManagerSpecialistEntry[],
  currentUserSub?: string,
): ManagerSpecialistEntry[] {
  const bySpecialist = new Map<string, ManagerSpecialistEntry[]>()
  for (const e of columnEntries) {
    const list = bySpecialist.get(e.specialist_sub) ?? []
    list.push(e)
    bySpecialist.set(e.specialist_sub, list)
  }

  const merged: ManagerSpecialistEntry[] = []
  for (const group of bySpecialist.values()) {
    const sorted = [...group].sort((a, b) => a.position - b.position)
    const own = currentUserSub
      ? sorted.find((e) => e.manager_sub === currentUserSub)
      : undefined
    const primary = own ?? sorted[0]
    if (!primary) continue
    const statusSource = sorted.find((e) => e.status_id) ?? primary
    const managerNames = [
      ...new Set(
        sorted
          .map((e) => e.manager_display_name?.trim())
          .filter((n): n is string => Boolean(n)),
      ),
    ]
    merged.push({
      ...primary,
      status_id: statusSource.status_id,
      status_title: statusSource.status_title,
      status_color: statusSource.status_color,
      manager_display_name:
        managerNames.length > 0 ? managerNames.join(', ') : primary.manager_display_name,
    })
  }
  return merged.sort((a, b) => a.position - b.position)
}
