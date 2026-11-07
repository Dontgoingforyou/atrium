import type { SharedDepartmentCalendar } from '../../types/calendar'

const OUTSTAFF_GID = '10000'

function namedDepartment(label: string): string {
  const text = label.trim()
  if (!text || /^\d+$/.test(text)) return ''
  return text
}

export function departmentLabel(gid: string | null | undefined): string {
  const text = gid?.trim() ?? ''
  if (!text) return 'Без отдела'
  if (text === OUTSTAFF_GID) return 'Аутстафф'
  return ''
}

export type { SharedDepartmentCalendar }

export type DepartmentCalendarGroup = {
  departmentId: string | null
  label: string
  calendars: SharedDepartmentCalendar[]
}

export function groupCalendarsByDepartment(
  calendars: SharedDepartmentCalendar[],
): DepartmentCalendarGroup[] {
  const buckets = new Map<string, DepartmentCalendarGroup>()
  for (const calendar of calendars) {
    if (!calendar.show_to_other_departments) continue
    const key = calendar.department_id ?? ''
    const existing = buckets.get(key)
    if (existing) {
      existing.calendars.push(calendar)
      continue
    }
    buckets.set(key, {
      departmentId: calendar.department_id,
      label: namedDepartment(calendar.department_label),
      calendars: [calendar],
    })
  }
  return [...buckets.values()].sort((left, right) => left.label.localeCompare(right.label, 'ru'))
}

export function departmentsMatchingQuery(
  groups: DepartmentCalendarGroup[],
  query: string,
): DepartmentCalendarGroup[] {
  const needle = query.trim().toLowerCase()
  if (!needle) return groups
  return groups.filter((group) => group.label.toLowerCase().includes(needle))
}

export function departmentGroupKey(group: DepartmentCalendarGroup): string {
  return group.departmentId ?? ''
}
