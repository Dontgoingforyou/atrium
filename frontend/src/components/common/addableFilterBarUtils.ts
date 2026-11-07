/** Плейсхолдер чипа, пока значения не выбраны. */
export const ADDABLE_FILTER_EMPTY_PLACEHOLDER = 'Выбрать…'

export type AddableFilterFieldSeed = {
  id: string
  hasValues: boolean
  defaultActive?: boolean
}

/** Текст чипа: «Статусы: В работе +1» или «Статусы: Выбрать…». */
export function formatFilterChipSummary(label: string, selectedLabels: readonly string[]): string {
  if (selectedLabels.length === 0) {
    return `${label}: ${ADDABLE_FILTER_EMPTY_PLACEHOLDER}`
  }
  if (selectedLabels.length === 1) {
    return `${label}: ${selectedLabels[0]}`
  }
  return `${label}: ${selectedLabels[0]} +${selectedLabels.length - 1}`
}

function shouldActivateField(field: AddableFilterFieldSeed): boolean {
  return Boolean(field.hasValues || field.defaultActive)
}

/** Поля с значениями или defaultActive — стартовый набор активных чипов. */
export function initActiveFieldIds(fields: readonly AddableFilterFieldSeed[]): string[] {
  return fields.filter(shouldActivateField).map((f) => f.id)
}

export function syncActiveFieldIds(
  prev: readonly string[],
  availableFields: readonly AddableFilterFieldSeed[],
): string[] {
  const availableIds = new Set(availableFields.map((f) => f.id))
  let next = prev.filter((id) => availableIds.has(id))
  for (const f of availableFields) {
    if (shouldActivateField(f) && !next.includes(f.id)) {
      next = [...next, f.id]
    }
  }
  return next
}

export function addActiveFieldId(activeIds: readonly string[], fieldId: string): string[] {
  if (activeIds.includes(fieldId)) return [...activeIds]
  return [...activeIds, fieldId]
}

export function removeActiveFieldId(activeIds: readonly string[], fieldId: string): string[] {
  return activeIds.filter((id) => id !== fieldId)
}

export function shouldOpenPickerOnAdd(field: {
  hasPicker: boolean
  openOnAdd?: boolean
}): boolean {
  if (!field.hasPicker) return false
  return field.openOnAdd !== false
}

export function shouldShowAddFilterMenu(inactiveFieldCount: number): boolean {
  return inactiveFieldCount > 0
}
