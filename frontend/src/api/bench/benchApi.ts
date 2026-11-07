import { authenticatedFetch } from '../rawClient'
import { parseJsonOrThrowApi } from '../parseResponse'
import { userFacingMessageFromApiFailure } from '../../utils/apiUserMessage'
import { filenameFromContentDisposition, triggerBlobDownload } from '../../utils/downloadBlob'
import type { BenchDashboard, BenchDashboardFilters } from '../../types/bench'

export function buildBenchQuery(filters: BenchDashboardFilters): string {
  const qs = new URLSearchParams()
  if (filters.year !== undefined) qs.set('year', String(filters.year))
  for (const spec of filters.specializations ?? []) {
    if (spec) qs.append('specialization', spec)
  }
  if (filters.month !== undefined) qs.set('month', String(filters.month))
  if (filters.dateFrom && filters.dateTo) {
    qs.set('date_from', filters.dateFrom)
    qs.set('date_to', filters.dateTo)
  }
  return qs.toString()
}

export async function fetchBenchDashboard(filters: BenchDashboardFilters): Promise<BenchDashboard> {
  const qs = buildBenchQuery(filters)
  const path = qs ? `/portal/bench/dashboard?${qs}` : '/portal/bench/dashboard'
  const res = await authenticatedFetch(path)
  return parseJsonOrThrowApi<BenchDashboard>(res)
}

export async function exportBenchDashboard(
  filters: BenchDashboardFilters,
  format: 'csv' | 'xlsx',
): Promise<void> {
  const qs = new URLSearchParams(buildBenchQuery(filters))
  qs.set('format', format)
  const res = await authenticatedFetch(`/portal/bench/export?${qs}`)
  if (!res.ok) {
    const bodyText = await res.text().catch(() => '')
    throw new Error(userFacingMessageFromApiFailure(res.status, bodyText))
  }
  const blob = await res.blob()
  const filename = filenameFromContentDisposition(
    res.headers.get('Content-Disposition'),
    `bench_dashboard.${format}`,
  )
  triggerBlobDownload(blob, filename)
}
