import type { BenchDashboardFilters } from '../../types/bench'

export const PORTAL_BENCH_DASHBOARD_ROOT_QUERY_KEY = ['portal', 'bench', 'dashboard'] as const

export function benchDashboardQueryKey(filters: BenchDashboardFilters) {
  return [...PORTAL_BENCH_DASHBOARD_ROOT_QUERY_KEY, filters] as const
}
