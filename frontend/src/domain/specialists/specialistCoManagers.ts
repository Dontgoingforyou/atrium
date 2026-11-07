import type { ManagerSpecialistEntry } from '../../types/specialist'

export function allManagersLabelForSpecialist(
  specialistSub: string,
  directoryEntries: ManagerSpecialistEntry[],
  currentUserSub?: string,
): string | null {
  const bySub = new Map<string, string>()
  for (const e of directoryEntries) {
    if (e.specialist_sub !== specialistSub) continue
    const name = e.manager_display_name?.trim() || e.manager_sub
    bySub.set(e.manager_sub, name)
  }
  if (bySub.size === 0) return null
  const subs = [...bySub.keys()].sort((a, b) => {
    if (a === currentUserSub) return -1
    if (b === currentUserSub) return 1
    return (bySub.get(a) ?? '').localeCompare(bySub.get(b) ?? '', 'ru')
  })
  return subs.map((s) => bySub.get(s)).join(', ')
}

export function enrichEntriesWithAllManagers(
  entries: ManagerSpecialistEntry[],
  directoryEntries: ManagerSpecialistEntry[],
  currentUserSub?: string,
): ManagerSpecialistEntry[] {
  return entries.map((entry) => ({
    ...entry,
    manager_display_name:
      allManagersLabelForSpecialist(entry.specialist_sub, directoryEntries, currentUserSub) ??
      entry.manager_display_name,
  }))
}

export type SpecialistBoardFilters = {
  managerSubs: string[]
  specialistSubs: string[]
}

export function entryMatchesBoardFilters(
  entry: ManagerSpecialistEntry,
  filters: SpecialistBoardFilters,
  directoryEntries: ManagerSpecialistEntry[],
  scope: 'my' | 'all',
): boolean {
  if (filters.specialistSubs.length > 0 && !filters.specialistSubs.includes(entry.specialist_sub)) {
    return false
  }
  if (filters.managerSubs.length === 0) return true
  if (scope === 'all') {
    return filters.managerSubs.includes(entry.manager_sub)
  }
  return directoryEntries.some(
    (d) =>
      d.specialist_sub === entry.specialist_sub &&
      filters.managerSubs.includes(d.manager_sub),
  )
}

export function filterBoardEntries(
  entries: ManagerSpecialistEntry[],
  filters: SpecialistBoardFilters,
  directoryEntries: ManagerSpecialistEntry[],
  scope: 'my' | 'all',
): ManagerSpecialistEntry[] {
  return entries.filter((e) => entryMatchesBoardFilters(e, filters, directoryEntries, scope))
}
