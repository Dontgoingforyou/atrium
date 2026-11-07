import type { PortalCounterparty } from '../../types/finance'

/** Активные контрагенты плюс текущий id, чтобы неактивный не пропадал из селекта при правке. */
export function counterpartiesForSelect(
  list: PortalCounterparty[] | undefined,
  keepId: string | null | undefined,
): PortalCounterparty[] {
  if (!list) return []
  return list.filter((c) => c.is_active || (keepId != null && keepId !== '' && c.id === keepId))
}
