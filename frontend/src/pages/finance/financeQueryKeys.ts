import type { QueryClient } from '@tanstack/react-query'

/** Корень ключей финансов — инвалидация префиксом. */
export const FINANCE_ROOT_QUERY_KEY = ['portal', 'finance'] as const

/** Лимит списков на экране финансов (бэкенд le=500). */
export const FINANCE_LIST_LIMIT = 200

export const financeQueryKeys = {
  root: FINANCE_ROOT_QUERY_KEY,
  summary: [...FINANCE_ROOT_QUERY_KEY, 'summary'] as const,
  contractsRoot: [...FINANCE_ROOT_QUERY_KEY, 'contracts'] as const,
  contracts: (status: string) => [...FINANCE_ROOT_QUERY_KEY, 'contracts', { status }] as const,
  invoicesRoot: [...FINANCE_ROOT_QUERY_KEY, 'invoices'] as const,
  invoices: (filters: { status: string; invoiceType: string }) =>
    [...FINANCE_ROOT_QUERY_KEY, 'invoices', filters] as const,
  payments: [...FINANCE_ROOT_QUERY_KEY, 'payments'] as const,
  counterparties: [...FINANCE_ROOT_QUERY_KEY, 'counterparties'] as const,
  procurementRequestsRoot: [...FINANCE_ROOT_QUERY_KEY, 'procurement-requests'] as const,
  procurementRequests: (status: string) =>
    [...FINANCE_ROOT_QUERY_KEY, 'procurement-requests', { status }] as const,
  procurementSummary: [...FINANCE_ROOT_QUERY_KEY, 'procurement-summary'] as const,
}

export function invalidateFinanceQueries(
  queryClient: QueryClient,
  ...keys: ReadonlyArray<readonly unknown[]>
): void {
  for (const queryKey of keys) {
    void queryClient.invalidateQueries({ queryKey })
  }
}
