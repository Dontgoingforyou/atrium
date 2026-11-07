export function firstNonEmptyColumnStatus(
  statusOrder: string[],
  itemCounts: ReadonlyMap<string, number>,
): string | null {
  for (const status of statusOrder) {
    if ((itemCounts.get(status) ?? 0) > 0) return status
  }
  return null
}
