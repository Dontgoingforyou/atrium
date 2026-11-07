export const SEARCHABLE_PICKER_PAGE_SIZE = 15

export type SearchablePickerOption = {
  value: string
  label: string
  secondary?: string | null
}

export function filterPickerOptions(
  options: SearchablePickerOption[],
  query: string,
  excludeValues: Set<string>,
): SearchablePickerOption[] {
  const q = query.trim().toLowerCase()
  return options.filter((opt) => {
    if (excludeValues.has(opt.value)) return false
    if (!q) return true
    return (
      opt.label.toLowerCase().includes(q) ||
      (opt.secondary?.toLowerCase().includes(q) ?? false) ||
      opt.value.toLowerCase().includes(q)
    )
  })
}

export function labelByValue(
  options: SearchablePickerOption[],
  value: string,
): string {
  return options.find((o) => o.value === value)?.label ?? value
}

export function paginateItems<T>(items: readonly T[], limit: number): {
  visible: T[]
  remaining: number
} {
  const safeLimit = Math.max(0, limit)
  return {
    visible: items.slice(0, safeLimit),
    remaining: Math.max(0, items.length - safeLimit),
  }
}
